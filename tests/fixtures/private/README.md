# QA-01 private evaluator fixtures

This directory is the isolated evaluator/oracle root for QA-only checks. Its contents are synthetic authored labels and analytic references, not partner/operator data, domain-reviewed truth, operational evidence, or an input to production code.

Do not copy this directory into public fixture bundles, detector/worker payloads, mock-server responses, frontend assets, or package outputs. Consumers that need a private expected value must load it explicitly in QA context; the public manifest does not reference or embed these files.
