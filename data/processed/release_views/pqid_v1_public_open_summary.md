# PQID License-Valid Release View

- export version: `pqid_license_valid_release_v1`
- profile: `public_open`
- description: Permissive-license rows only.
- included license categories: `permissive`
- manually reviewed other licenses: `none`
- total input rows: `550,314`
- total exported rows: `360,768`
- total excluded rows: `189,546`

## Split Counts

| split      | input_rows | exported_rows | excluded_rows |
| ---------- | ---------- | ------------- | ------------- |
| train      | 440580     | 288744        | 151836        |
| validation | 55110      | 36198         | 18912         |
| test       | 54624      | 35826         | 18798         |

## Exported License Categories

| license_category | rows   |
| ---------------- | ------ |
| permissive       | 360768 |

## Excluded License Categories

| license_category | rows   |
| ---------------- | ------ |
| copyleft         | 7356   |
| no_license       | 181488 |
| other            | 702    |

## Release Rule

Rows with `license_category` outside the selected profile are excluded from this release view.
`no_license` rows are not exported. Residual missing license-category rows, if present, are treated as restricted governance-metadata gaps.
`other` rows are exported only when their detected license appears in the manual review override list.
Copyleft rows, when included by profile, remain marked as `public_open_with_obligations` and should not be presented as obligation-free.
