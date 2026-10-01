# Encrypted Backup and Restore Runbook

## Status

This runbook defines the manually approved backup and recovery procedure for
the Phase 4 n8n production-hardening baseline.

Provider-managed backups remain disabled by deliberate cost decision. The
approved alternative is an encrypted off-server backup retained on an
authorized Ubuntu recovery host.

## Scope

The backup protects:

- n8n SQLite data and write-ahead-log files
- n8n workflow, credential, and application state
- PostgreSQL through a custom-format logical dump
- MySQL through a transaction-consistent logical dump
- the Docker Compose definition
- protected environment configuration
- the n8n encryption key
- database recovery credentials required by the deployment
- component checksums and non-secret recovery metadata

The procedure does not:

- enable public ingress
- create SSH credentials
- place passphrases in commands, files, or environment variables
- automate production changes
- authorize an in-place production restore
- replace independent infrastructure-recovery controls

## Trust boundaries

- Docker commands use the existing approved sudo path.
- The server account does not receive Docker-group membership.
- n8n remains bound to the server loopback interface.
- Transfers use an already authorized SSH client.
- Server host keys are authenticated before first use.
- Only encrypted backup material may leave the server.
- The passphrase is stored separately in an approved password manager.
- Temporary plaintext is root-readable only.
- A production restore requires separate human approval.

## Recovery architecture

~~~text
n8n server
  -> native PostgreSQL and MySQL logical dumps
  -> controlled n8n stop for consistent SQLite capture
  -> protected recovery package
  -> GPG symmetric AES-256 encryption
  -> authenticated SSH transfer
  -> encrypted Ubuntu recovery copy
  -> checksum, decryption, and component validation
~~~

## Required variables

Set fresh values for every execution:

~~~bash
backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_work="$(
  sudo mktemp -d     "/var/tmp/n8n-backup-${backup_stamp}.XXXXXX"
)"
backup_plain="/var/tmp/n8n-backup-${backup_stamp}.tar.gz"
backup_encrypted="${backup_plain}.gpg"
backup_checksum="${backup_encrypted}.sha256"
~~~

The server working directory must be owned by root with mode `700`.

## Pre-flight checks

Before creating a backup:

1. Confirm the approved maintenance window.
2. Confirm the Ubuntu destination has sufficient capacity.
3. Confirm the backup passphrase is retrievable.
4. Confirm all three containers are healthy.
5. Confirm required native tools exist.
6. Confirm the target paths do not already exist.
7. Confirm no unrelated production change is in progress.

~~~bash
sudo docker compose   -f /opt/n8n/compose.yaml   ps
~~~

Stop if any container is unhealthy.

## Create the PostgreSQL dump

Use PostgreSQL's native custom format:

~~~bash
sudo env BACKUP_WORK="$backup_work"   bash -c '
    set -euo pipefail
    umask 077
    docker compose       -f /opt/n8n/compose.yaml       exec -T postgres       sh -c '"'"'
        pg_dump           --format=custom           --username="$POSTGRES_USER"           --dbname="$POSTGRES_DB"
      '"'"'       > "$BACKUP_WORK/postgres.dump"
  '
~~~

The command must exit successfully and create a nonempty file.

## Create the MySQL dump

Use a transaction-consistent logical dump:

~~~bash
sudo env BACKUP_WORK="$backup_work"   bash -c '
    set -euo pipefail
    umask 077
    docker compose       -f /opt/n8n/compose.yaml       exec -T mysql       sh -c '"'"'
        MYSQL_PWD="$MYSQL_PASSWORD"         mysqldump           --single-transaction           --quick           --no-tablespaces           --user="$MYSQL_USER"           "$MYSQL_DATABASE"
      '"'"'       > "$BACKUP_WORK/mysql.sql"
  '
~~~

The command must exit successfully and create a nonempty file.

## Capture consistent n8n data

SQLite and its write-ahead log must be captured while n8n is stopped.
PostgreSQL and MySQL remain online.

Use a restart trap so n8n is started if archive creation fails:

~~~bash
sudo env BACKUP_WORK="$backup_work"   bash -c '
    set -euo pipefail

    compose_file=/opt/n8n/compose.yaml
    n8n_started=0

    restart_n8n() {
      if [ "$n8n_started" -eq 0 ]; then
        docker compose           -f "$compose_file"           start n8n >/dev/null
      fi
    }

    trap restart_n8n EXIT

    docker compose       -f "$compose_file"       stop n8n

    umask 077

    tar       --acls       --xattrs       --numeric-owner       -C /srv/n8n       -cpf "$BACKUP_WORK/n8n-data.tar"       data

    config_files=(compose.yaml .env)

    if [ -f /opt/n8n/.postgres-reader-password ]; then
      config_files+=(.postgres-reader-password)
    fi

    tar       --numeric-owner       -C /opt/n8n       -cpf "$BACKUP_WORK/deployment-config.tar"       "${config_files[@]}"

    docker compose       -f "$compose_file"       start n8n

    n8n_started=1
    trap - EXIT
  '
~~~

Confirm that n8n returns to `healthy` before continuing.

## Validate the components

Required validation:

- `tar -tf` succeeds for both tar archives.
- `pg_restore --list` recognizes the PostgreSQL dump.
- The MySQL dump contains its completion marker.
- Every component is nonempty.
- Temporary files are root-owned with mode `600`.

Create `backup-metadata.txt` containing only non-secret recovery information.

Create `component-sha256.txt` covering:

- `backup-metadata.txt`
- `deployment-config.tar`
- `mysql.sql`
- `n8n-data.tar`
- `postgres.dump`

Run `sha256sum --check component-sha256.txt` before packaging.

## Package the recovery components

~~~bash
sudo tar   -C "$backup_work"   -czf "$backup_plain"   backup-metadata.txt   component-sha256.txt   deployment-config.tar   mysql.sql   n8n-data.tar   postgres.dump

sudo chmod 600 "$backup_plain"
~~~

## Encrypt the package

Create an isolated root-only GPG home:

~~~bash
gpg_home="$backup_work/gnupg-home"

sudo install   -d   -o root   -g root   -m 700   "$gpg_home"
~~~

Encrypt without placing the passphrase in a command or environment variable:

~~~bash
sudo env GPG_TTY="$(tty)"   gpg   --homedir "$gpg_home"   --no-options   --pinentry-mode loopback   --no-symkey-cache   --symmetric   --cipher-algo AES256   --s2k-mode 3   --s2k-digest-algo SHA512   --output "$backup_encrypted"   "$backup_plain"
~~~

Enter the passphrase only at GPG's private prompt.

Validate decryption by piping the result to `tar -tzf -`. Do not retain a
second plaintext package.

Create a SHA-256 checksum for the encrypted file.

## Transfer the encrypted backup

Transfer only:

- `n8n-backup-<timestamp>.tar.gz.gpg`
- `n8n-backup-<timestamp>.tar.gz.gpg.sha256`

Use an already authorized SSH path. Do not copy private SSH keys merely to
perform a transfer.

Authenticate an unfamiliar server host key by comparing its authoritative
ED25519 fingerprint with the fingerprint received by the transfer host.

## Validate the off-server copy

On the Ubuntu recovery host:

1. Store the files in a user-owned mode-`700` directory.
2. Set both files to mode `600`.
3. Run `sha256sum --check` against the encrypted archive.
4. Decrypt into a randomly named mode-`700` validation directory.
5. Validate `component-sha256.txt`.
6. Open both tar catalogs.
7. Verify the MySQL completion marker.
8. Verify the PostgreSQL dump and metadata are nonempty.
9. Remove the plaintext validation directory.
10. Confirm only the encrypted archive and checksum remain.

A backup is not accepted until this independent validation passes.

## Cleanup

Cleanup is allowed only after off-server validation passes.

Before deletion:

- print every target path
- verify every path contains the current backup timestamp
- refuse broad, empty, unresolved, or unexpected paths

Remove only:

- the root-only server working directory
- the server plaintext package
- the server encrypted duplicate
- the server checksum duplicate
- the user-readable server transfer directory
- any temporary Windows or shared-folder transfer copy

Never use a broad home, root, `/var/tmp`, `/srv`, or wildcard deletion target.

## Restore approval gate

A production restore is destructive and requires explicit approval after:

- the target server and incident are identified
- the selected backup timestamp is confirmed
- the encrypted checksum passes
- the passphrase is available
- the recovery point is accepted
- current production data is preserved when possible
- rollback and abort criteria are documented
- application downtime is approved

Do not restore over a running deployment.

## Restore order

Restore in this order:

1. Verify the encrypted-file checksum.
2. Decrypt into a root-only temporary recovery directory.
3. Validate all component checksums.
4. Review the non-secret recovery metadata.
5. Recreate the approved directory and permission structure.
6. Restore the protected deployment configuration.
7. Confirm the original n8n encryption key is present.
8. Recreate the pinned containers without starting n8n.
9. Restore PostgreSQL with `pg_restore`.
10. Restore MySQL with the native MySQL client.
11. Restore the n8n data archive while n8n is stopped.
12. Start PostgreSQL and MySQL and verify health.
13. Start n8n and verify health.
14. Validate login, workflows, credentials, and read-only probes.
15. Remove temporary plaintext after acceptance.

The n8n encryption key must match the restored credential data. A different
key can make stored credentials unusable.

## Isolated restore drill

Prefer an isolated host or Docker project with:

- no production ports
- no public ingress
- separate directories
- separate networks
- no unauthorized external operational actions

Catalog and checksum validation does not replace a full isolated restore
drill.

## Retention

Current cost-controlled policy:

- create an encrypted backup after a material deployment or configuration
  change
- retain the latest validated recovery point
- retain older points only within available Ubuntu capacity
- delete an older point only after a newer backup passes validation
- keep the passphrase outside the server and backup directory

## Failure handling

If any step fails:

1. Stop the backup procedure.
2. Ensure n8n is running and healthy.
3. Retain protected temporary data until the failure is understood.
4. Do not transfer unencrypted data.
5. Do not delete the last validated recovery point.
6. Record the failed command and non-secret error.
7. Require approval before retrying a destructive operation.

## Acceptance criteria

A backup is accepted only when:

- all source components were captured successfully
- n8n returned to healthy
- component checksums passed
- encryption succeeded
- decryption and archive validation succeeded
- the transfer checksum passed
- independent Ubuntu recovery validation passed
- passphrase custody was confirmed
- temporary plaintext and transfer copies were removed
- the previous validated backup was not removed prematurely
