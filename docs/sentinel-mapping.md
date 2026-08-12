# Microsoft Sentinel mapping

> **Status: placeholder. Written at M6.**
>
> **Documented, not deployed.** No Azure resources are created and no Azure
> spend is incurred by this project. This was locked at planning and is not
> revisited.

Planned contents:

1. A Sentinel custom table schema covering the ASTP field register, with column
   types and the naming rules Sentinel imposes.
2. A Data Collection Rule shape showing how JSON Lines events would reach that
   table.
3. Notes on which fields need transformation on ingest, and which of the Sigma
   rules in `detect/sigma/` translate cleanly.

Every claim about Sentinel schema constraints or Data Collection Rule behaviour
is cited to Microsoft documentation with a retrieval date.
