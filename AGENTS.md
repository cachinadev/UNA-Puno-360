# UNA Puno 360 contributor notes

- Preserve the extracted `UNA_Data_Hub_v*` folders as source evidence. The consolidated application lives under `apps/`, `services/`, and `packages/`.
- Never present demonstration records as official UNA data or simulated vehicle positions as live GPS.
- Keep backend authorization checks on every admin/moderation operation; hidden navigation is not authorization.
- Run `scripts/test.ps1` before claiming a change is complete. Docker-dependent checks may be skipped only with an explicit reason.
- Use Spanish for user-facing copy. English, Quechua, and Aymara are locale placeholders until reviewed translations exist.
