# I Removed Every Field From My AI Logs to Find Out Which Ones Matter

*Only two of the seven fields I added for security could be tested at all. Both were required. The claim came back undertested.*

Everyone agrees you should log your LLM applications. Almost nobody says which fields, and the closest thing to a standard, the OpenTelemetry GenAI semantic conventions, is built for observability rather than detection. So I built an agent, attacked it, and then removed each field from the captured logs to see which detections went dark.

I expected the fields that matter most to be the security fields the conventions leave out. That claim is **undertested**: only two of my seven security-only fields could be tested at all, and both turned out to be required. Undertested is the reading I settled on after the detector baseline was known, though before the ablation ran. The rule I'd set before the first capture says **weakened**, because the other five came out as not required. It doesn't say refuted: none of the fields that went dark is one the conventions fully cover. Both words are the result, and this post is about why they differ.

## What exists already

The OpenTelemetry GenAI semantic conventions name attributes for model calls, token usage, tool calls, retrieval and agents. They're the right base, and my profile adopts their `gen_ai.*` names wherever an equivalent exists. They're also still moving. When I pinned them in August every GenAI attribute was at Development status and no release had been published, and when I checked again on 1 October 2026 that was still true.

They were built for observability, cost and quality, and it shows in what's missing. Nothing records whether retrieved content came from a trusted source, or whether the caller was entitled to it. Nothing records which documents were in the model's context when it decided to call a tool, where an outbound call was going as a value you can compare against an allow list, or whether a planted marker left the system. Those gaps are the seven fields my profile flags as security-only, and they were the hypothesis.

Governance has the same gap. The UK's Code of Practice for the Cyber Security of AI and its ETSI counterpart, TS 104 223, both say to log system and user actions, and neither says which fields a log needs for detection.

Of the profile's 37 fields, 13 map fully to an attribute of the conventions, 6 map partially and 18 have no equivalent at all.

## The instrument

Everything is public at [github.com/quisumego/ai-security-telemetry-profile](https://github.com/quisumego/ai-security-telemetry-profile): the specification, the agent, the attacks, every capture and every result.

![Two report commands rebuilding the results from the saved captures](https://github.com/quisumego/ai-security-telemetry-profile/raw/main/docs/demo.gif)

The lab is a deliberately small agent on the Claude Agent SDK, pinned to `claude-haiku-4-5`, working for a fictional UK insurer called Thornfield Mutual. It has six tools: document search, a claims lookup, a case file reader, a case note writer, email and a URL fetcher. Its synthetic document estate holds policy wordings, procedures, underwriting notes, outside correspondence, and the files of a second tenant it should never read. Nothing it does reaches the network: email is written to a file, fetched pages are served from fixtures, and every destination it is configured with is under the `.invalid` domain.

Ten attack classes, numbered A1 to A10 in this order, follow the OWASP Top 10 for LLM Applications, with MITRE ATLAS techniques cross-referenced: direct and indirect prompt injection, sensitive information disclosure, tool misuse, improper output handling, retrieval poisoning, system prompt leakage, unbounded consumption, cross-tenant retrieval and a staged exfiltration chain. Each ran ten times, and each has an oracle, written before the runs, that decides success mechanically. Canaries, unique strings planted in restricted documents, claim records and the system prompt, turn "did it leak?" into a string match rather than a judgement.

Every event the agent emits is a line of JSON in six groups: session, turn, content, retrieval, action and control. The 100 attack trials and 100 benign sessions were captured once and saved, and everything after that reads them: the ablation calls no model at all.

## The method

The rules came first. Before any capture, I set and locked the rule that turns measurements into tiers. A field is Required if removing it makes at least one attack class undetectable, and Recommended if removing it degrades detection materially, a fall of 20 percentage points or more, or a false positive rate pushed above 10 per cent, with nothing going dark. It's Optional if removing it has no measurable effect but a reason to keep it was written down beforehand, and Not required if it has neither.

Two of the ten classes were held out: no detector was written for them, and they were opened only after the detector set was frozen. The seven detectors were written against throwaway fixtures, never against a capture. Then the ablation: each field set to null in the captured logs, singly and in pairs within a group, and every detector re-run, with no model call anywhere. No step in the scoring is decided by hand.

## The results

The sweep nulled 37 fields singly and 103 pairs. 3 fields tier Required, 0 Recommended, 10 Optional and 24 Not required.

The matrix is thin, and that's the first finding. A field can only go dark for a class that has a successful attack to detect, and on the pinned model five of the ten classes produced one. The model refused what it could recognise as an attack and complied with what looked like correct work: following a retrieved procedure, reading a long document in full, serving a claim lookup by reference. Three worked examples show what the matrix can and can't say.

Start with the field that turned out load-bearing, `retrieval.document_ids`. Retrieval poisoning, a planted procedure document, succeeded in every trial and was detected in every one, by a rule that asks whether a retrieved document belongs to the indexed estate. Null the document identifiers and detection falls from 10/10 to 0/10. The class goes dark, so the field is Required.

Then the field the measurement couldn't reach, `action.context_document_ids`. I'd predicted it would be the most important field in the profile. It records which retrieved documents were in the model's context when it called a tool, which is the link between an injected document and the action it causes. No detector read it, so it tiers Not required, and that tier says nothing about whether it carries signal. Five of the seven security-only fields are in the same position: never read by a detector with a successful attack to detect.

The surprise was `action.egress_target`. The oracle for direct prompt injection, a canary leaving by email, fired on 1 of 100 benign sessions and on none of the 10 attack trials. The model refused the attack every time, and one ordinary session emailed a tracked reference to a permitted internal recipient. As a signal, that oracle's precision is zero. What separates the attack from the benign session is the destination, which is exactly what `action.egress_target` records, and the detector that reads it fired on 0/100 benign sessions. But the rule only credits a field for the detections it protects. With no successful attack, there was nothing to protect, and the field tiers Not required. The canary was not the signal. The canary together with the destination was.

## The vendor gap

What would Microsoft Foundry and Amazon Bedrock give you by default? I read their logging documentation on 23 September 2026 and re-ran the detectors over the captures with everything a vendor surface does not record taken away. None of the seven security-only fields is available on any of the 6 surfaces assessed: each is held only by the deployment, or derived by it. With vendor defaults only, no class is shown to stay detectable on any single surface. Unbounded consumption is unconfirmed on the as-shipped and model layers, because Bedrock does not say whether its input token count includes cached tokens and Azure documents no per-call token count at all.

Two cautions. This rests on documentation, not on log records I observed. And most of the fields Azure could record are unconfirmed rather than absent, because Azure documents only the header its resource logs share. The vendor gap supports the case for a profile. It doesn't test my headline claim, and I keep the two apart.

## Limitations

The weakest joint is circularity. I designed the schema, wrote the attacks and wrote the detectors, and detectors tend to find necessary the fields their author chose to emit. Writing them against behaviour, from fixtures, and holding two classes out reduces that. It doesn't remove it, and no one independent has reviewed the scenarios, the oracles or the detectors. I built it with Claude Code, an AI coding assistant, which wrote the code to designs I ruled on: that's help, not review. Everything is published so it can be checked. The corpus is small and synthetic, too: ten trials per class and 100 benign sessions.

The holdout result needs its caveat. The detector written for sensitive information disclosure caught 10 of 10 successful A9 cross-tenant trials with 0/100 benign false positives. That A9 result carries its exposure: the Claude Code session that built the detectors knew both holdout outcomes, my own project notes at the time disclosed A9's retrieval signature to any session that read them, the detectors were authored from fixtures only, and the result is weakened evidence, not a clean holdout.

The model is the other limit. I re-ran the attacks on a small local model, `granite4.1:3b`, through Ollama: 18/91 successes against 32/100, and the classes that succeeded changed, not only how often. Over that pass one tier would move, `action.egress_target` to Required, and the headline would read the same. It's one comparison, run on a CPU with two classes unmeasured, through a route Anthropic says it doesn't support, so I report it beside the tiers and never apply it.

Two more belong here. Undertested was ruled after the baseline was known, which is why weakened sits beside it everywhere. And the Microsoft Sentinel queries I wrote for the detectors have never run, while the volume figures describe this lab's events, which never log a tool result. The full list is in the specification, and it's longer than this one.

## What to do on Monday

Add the three fields that went dark when removed. `retrieval.document_ids`, so a planted or unexpected document can be found in the log rather than in the answer. `retrieval.permission_context`, the caller's scope beside each returned document's scope, tenant included, because a boundary crossing is only visible if both sides are logged. And `control.canary_triggered`, computed at the source before any text is hashed or cut, because a planted string turns exfiltration into a string match.

Keep two more whatever a tier table says. `session.id`, because a real pipeline needs it to put a session back together. And the destination of every outbound call, `action.egress_target`, because in this corpus the destination, not the payload, was what separated an attack from ordinary work.

Then measure your own. These tiers are evidence about one schema, one agent and one model on a synthetic corpus, and they won't transfer as they stand. The method will, and the repository has everything needed to repeat it. If you log an agent, start with the [field register](https://github.com/quisumego/ai-security-telemetry-profile/blob/main/SPEC.md#3-the-field-register): every field, with the evidence behind its tier.
