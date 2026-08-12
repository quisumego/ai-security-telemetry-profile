# Vendor gap analysis

> **Status: placeholder. Written at M7.**

Assesses Azure AI Foundry diagnostic logging and AWS Bedrock model invocation
logging against the ASTP field register, then answers the question that matters:
**with vendor defaults only, which of the ten attack classes stay detectable?**

Planned structure:

1. For each vendor, every field in the register classified as available by
   default, available with configuration, or absent.
2. For each vendor, the attack classes that remain detectable using defaults
   alone.
3. The fields a deployment has to add itself, in priority order.

**Evidence rule for this file.** Every claim about vendor behaviour is cited to
vendor documentation with a retrieval date. No claim about what a vendor logs is
made from memory. If a capability cannot be confirmed from documentation, it is
recorded as unconfirmed rather than assumed either way.
