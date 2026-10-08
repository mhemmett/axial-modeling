# Known issues

- The provided PyLith tarball extracts and `pylith --version` reports 5.0.2.
  Its bundled Gmsh cannot load because this host lacks `libGLU.so.1`. Installing
  the missing system library needs administrator privileges; the Conda
  environment specification includes Gmsh and its user-space libraries.
- The `axial-modeling` Conda environment could not be created in this session.
  Conda package caches are outside the writable workspace and outbound DNS is
  unavailable, so the required packages could not be fetched. The complete
  environment is specified in `environment.yml`.
- The main article's publisher HTML and figure captions were available through
  the browser, but the article and supplement PDFs could not be downloaded from
  the shell because outbound DNS is unavailable. Supplement-only parameters
  and panel IDs remain unresolved in `docs/parameters.yaml` and
  `docs/figure_reproduction.md`; do not fill those gaps with author code,
  source data, or plot digitization.
- `gh` is not installed and neither `GH_TOKEN` nor `GITHUB_TOKEN` is present.
  SSH access to `mhemmett/axial-modeling` fails with `Permission denied
  (publickey)`, and HTTPS cannot obtain credentials in this session. The local
  repository can be committed, but pushing and pull-request creation remain
  pending. Do not generate a replacement key or request a deploy key for the
  account key.
- The installed `tmux` 3.8 executable cannot create a server socket in either
  `/tmp` or the repository because this session's sandbox denies Unix-socket
  operations. A persistent session must be started from the host terminal.
