# PQID License-Valid Release View

- export version: `pqid_license_valid_release_v1`
- profile: `license_valid`
- description: License-resolved rows: permissive, copyleft, and manually reviewed other-license rows with obligations preserved.
- included license categories: `copyleft, other, permissive`
- manually reviewed other licenses: `BSD-3-Clause-Clear, CC-BY-4.0, EPL-2.0, MulanPSL-2.0`
- total input rows: `550,314`
- total exported rows: `319,782`
- total excluded rows: `230,532`

## Split Counts

| split      | input_rows | exported_rows | excluded_rows |
| ---------- | ---------- | ------------- | ------------- |
| train      | 440580     | 255852        | 184728        |
| validation | 55110      | 32088         | 23022         |
| test       | 54624      | 31842         | 22782         |

## Exported License Categories

| license_category | rows   |
| ---------------- | ------ |
| copyleft         | 7356   |
| other            | 702    |
| permissive       | 311724 |

## Excluded License Categories

| license_category | rows   |
| ---------------- | ------ |
| no_license       | 230532 |

## Release Rule

Rows with `license_category` outside the selected profile are excluded from this release view.
`no_license` rows are not exported. Residual missing license-category rows, if present, are treated as restricted governance-metadata gaps.
`other` rows are exported only when their detected license appears in the manual review override list.
Copyleft rows, when included by profile, remain marked as `public_open_with_obligations` and should not be presented as obligation-free.
