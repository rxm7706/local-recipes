# pyforge-doctor

Pre-flight + fleet-watch diagnostics CLI (`doctor check` / `doctor monitor` /
`doctor diagnose`) consolidating [`pyforge-warden`](../pyforge-warden) +
`cf_atlas` signals into one schema-validated `DoctorReport` envelope and its
own exit-code gate.