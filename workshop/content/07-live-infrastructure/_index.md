---
title: "Module 7: Live AWS Infrastructure"
chapter: true
weight: 70
---

# Module 7: Live AWS Infrastructure (Optional)

In this module, you'll deploy the full data infrastructure on AWS and switch the agent from simulated data to querying real services.

{{% notice warning %}}
**Cost Warning:** This module provisions Aurora Serverless v2, Timestream, Redshift Serverless, OpenSearch Serverless, and supporting services. Estimated cost: **$15–25/hour while running** (primarily OpenSearch Serverless at $0.24/OCU-hour × 2 OCU minimum). **Clean up immediately after testing.**
{{% /notice %}}

{{% notice info %}}
**Skip this module** if you're short on time or don't need to demonstrate live data connectivity. The simulated mode demonstrates the full architecture pattern without AWS infrastructure costs.
{{% /notice %}}
