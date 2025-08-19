

This project is a credential management platform, which can issue credentials and revoke credentials.

This folder includes a Angular frontend and python(flask) backend, and a postgres database. 

postgres data use goose to for database migration.

credential
Credential ID	Subject ID	Type	Format	Status	Issued	Expires	Actions

verification_log
Checked At	Credential ID	Result	Response Time	Verifier