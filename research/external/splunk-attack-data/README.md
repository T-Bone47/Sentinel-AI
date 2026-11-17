# Splunk attack_data samples (third-party)

The five files in this folder are **copied unmodified** from Splunk's
**attack_data** repository: github.com/splunk/attack_data, branch `master`,
retrieved 2026-11-17.

- **Licence:** Apache License 2.0. A copy of the licence is in this
  repository's root `LICENSE`.
- **NOTICE:** the upstream repository has no `NOTICE` file (checked
  2026-11-18).
- **Not our work.** Splunk is a trademark of Splunk Inc. It is named here only
  to say where the files came from; this project is not affiliated with or
  endorsed by Splunk.
- **What they contain:** identities, AWS account identifiers and network
  addresses from Splunk's own lab environment, as Splunk published them.

| File (this folder) | Upstream path under `datasets/attack_techniques/` | Bytes | SHA-256 |
|---|---|---|---|
| `T1110.001-aws_login_failure/aws_cloudtrail_events.json` | `T1110.001/aws_login_failure/` | 8,107 | `d9d0ebbaf9a6aebd504b03f665eb1f35dfee4e34c0c6a5cf1c5318b7a12c1e9b` |
| `T1110.001-azure_ad_high_number_of_failed_authentications_for_user/azuread.log` | `T1110.001/azure_ad_high_number_of_failed_authentications_for_user/` | 105,311 | `1d5c729dc5e864ca2894cceae832ff4119f17a709e1ec33838b3f60baab3af87` |
| `T1098-aws_iam_delete_policy/aws_iam_delete_policy.json` | `T1098/aws_iam_delete_policy/` | 107,317 | `862f9c73569bcdd38006b242bcdcd82b1424cabaaee01c4f931732e5f4c04b33` |
| `T1098-aws_iam_successful_group_deletion/aws_iam_successful_group_deletion.json` | `T1098/aws_iam_successful_group_deletion/` | 77,518 | `6f526a69b82e0d53ef733e79f44e6422bd599af51d2f31896b853ded069c3396` |
| `T1098-aws_iam_failure_group_deletion/aws_iam_failure_group_deletion.json` | `T1098/aws_iam_failure_group_deletion/` | 47,083 | `3dae36751402bc19f86cecfac3f622ac41ef6d4c4ede6f334e3b7fbcde35a991` |

**Where they are used:** the pinned tests in
`sentinel-ai-backend/tests/test_gate2_events.py` check these exact bytes; they
skip if the files are absent. What the files can and cannot test is in
`research/M2_REPORT.md` and `docs/M2_DATASET_SHORTLIST.md`.

`.gitattributes` marks this folder `-text`, so git never rewrites line endings
and the hashes hold on every platform.
