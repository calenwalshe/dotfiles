# Credential Management

Credentials are stored in `pass` (GPG-encrypted password store).

## Setup

- GPG Key: `6FBF2CFF535EC48D` (Ross Walshe <ross@radio-ops>)
- Password store: `~/.password-store/`

## Stored Entries

| Entry | Command |
|-------|---------|
| FCC ULS login | `pass show radio/fcc-uls` |

## Quick Reference

```bash
# View FCC ULS credentials
pass show radio/fcc-uls

# Edit credentials
pass edit radio/fcc-uls

# Add a new entry
pass insert -m radio/new-entry

# Copy password to clipboard (if xclip installed)
pass -c radio/fcc-uls
```

## FCC ULS Portal

- URL: https://wireless2.fcc.gov/UlsEntry/licManager/login.jsp
- Use `pass show radio/fcc-uls` to retrieve login details

## Important

- GPG passphrase is NOT stored digitally — write it down physically
- To add a passphrase to the GPG key later: `gpg --edit-key 6FBF2CFF535EC48D passwd`
