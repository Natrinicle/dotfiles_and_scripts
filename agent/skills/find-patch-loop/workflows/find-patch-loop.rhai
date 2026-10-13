let meta = #{
    name: "find-patch-loop",
    description: "Hunt bugs with finders, refute with skeptics, propose patches",
    when_to_use: "multi-agent bug hunt, tester bots vs coder bots, find-fix-retest",
    phases: [
        #{ title: "Hunt", detail: "scoped finders file evidence-backed reports" },
        #{ title: "Skeptic", detail: "one skeptic per report tries to refute it" },
        #{ title: "Propose", detail: "one patcher per confirmed id proposes a diff" },
    ],
};

let findings_schema = #{
    "type": "object", "required": ["findings"],
    "properties": #{
        "findings": #{ "type": "array", "maxItems": 8, "items": #{
            "type": "object",
            "required": ["title", "repro", "evidence"],
            "properties": #{
                "title": #{ "type": "string" },
                "scope": #{ "type": "string" },
                "repro": #{ "type": "string" },
                "expected": #{ "type": "string" },
                "actual": #{ "type": "string" },
                "evidence": #{ "type": "string" },
            },
        }},
    },
};
let verdict_schema = #{
    "type": "object", "required": ["verdict", "reason", "evidence"],
    "properties": #{
        "verdict": #{ "type": "string", "enum": ["real", "false", "needs-info"] },
        "reason": #{ "type": "string" },
        "evidence": #{ "type": "string" },
    },
};
let patch_schema = #{
    "type": "object", "required": ["id", "summary", "diff"],
    "properties": #{
        "id": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "diff": #{ "type": "string" },
        "test_command": #{ "type": "string" },
    },
};

let target = if args == () { () } else { args.target };
if target == () { pause("verification", "Pass args.target — the path, package, or tree to hunt."); }

let target_json = json_encode(target);

phase("Hunt");
let scopes = ["crashes and assertion failures", "wrong results and logic bugs", "error-handling gaps"];
let hunt_jobs = [];
for s in scopes {
    let hp = "";
    hp += "You are a bug finder. Hunt only for ";
    hp += s;
    hp += " in this target: ";
    hp += target_json;
    hp += ". Use read-only tools (read_file, grep, git diff). Run existing tests when a runner is obvious. ";
    hp += "Do not patch. Do not answer from memory. Report at most 8 findings as ";
    hp += "{title, scope, repro, expected, actual, evidence}. evidence must be command output you collected. ";
    hp += "Run the project's tests or the queue CLI when a runner is obvious. ";
    hp += "An empty list is valid only after you ran tests or read the code.";
    hunt_jobs.push(#{
        prompt: hp,
        label: "finder:" + s,
        capability_mode: "execute",
        output_schema: findings_schema,
    });
}
let hunt_results = parallel(hunt_jobs);

let findings = [];
let hunt_failed = 0;
for r in hunt_results {
    if r == () || !r.success {
        hunt_failed += 1;
    } else if r.output.findings != () {
        for f in r.output.findings { findings.push(f); }
    }
}
log(findings.len().to_string() + " raw findings; " + hunt_failed.to_string() + " hunt slots failed");
if findings.len() == 0 {
    if hunt_failed > 0 {
        complete(#{ summary: "Hunt failed; unverified.", confirmed: [], patches: [], hunt_failed: hunt_failed });
    }
    complete(#{ summary: "No findings.", confirmed: [], patches: [] });
}

phase("Skeptic");
let vjobs = [];
for f in findings {
    let fjson = json_encode(f);
    let vp = "";
    vp += "You are a bug skeptic. Your job is to prove this report wrong. Target: ";
    vp += target_json;
    vp += " Report: ";
    vp += fjson;
    vp += " Re-run the repro with the shell (python3 / the queue CLI). Set verdict=real only with command output you collected. ";
    vp += "If you cannot run the repro, set verdict=needs-info. Failed or missing skeptic is unverified, not verdict=false. Do not patch.";
    vjobs.push(#{
        prompt: vp,
        label: "skeptic",
        capability_mode: "execute",
        output_schema: verdict_schema,
    });
}
let verdicts = parallel(vjobs);

let confirmed = [];
let skeptic_failed = 0;
let i = 0;
for v in verdicts {
    if v == () || !v.success {
        skeptic_failed += 1;
    } else if v.output.verdict == "real"
        && v.output.evidence != () && v.output.evidence != "" {
        confirmed.push(findings[i]);
    }
    i += 1;
}
log(confirmed.len().to_string() + "/" + findings.len().to_string() + " survived skepticism; " + skeptic_failed.to_string() + " skeptic slots failed");
if confirmed.len() == 0 {
    if skeptic_failed > 0 {
        complete(#{ summary: "Skeptics failed; unverified.", confirmed: [], patches: [], skeptic_failed: skeptic_failed });
    }
    complete(#{ summary: "No confirmed bugs.", confirmed: [], patches: [] });
}

phase("Propose");
let pjobs = [];
let pi = 0;
for c in confirmed {
    let cjson = json_encode(c);
    let n = pi + 1;
    let idn = if n < 10 { "BUG-00" + n.to_string() } else if n < 100 { "BUG-0" + n.to_string() } else { "BUG-" + n.to_string() };
    let pp = "";
    pp += "You are a bug patcher. Propose a minimal unified diff for ";
    pp += idn;
    pp += " in target ";
    pp += target_json;
    pp += " Confirmed bug: ";
    pp += cjson;
    pp += " Do not commit. Do not expand scope. Keep any failing test the finder described. ";
    pp += "Return {id, summary, diff, test_command}. id must be ";
    pp += idn;
    pp += ".";
    pjobs.push(#{
        prompt: pp,
        label: "patcher:" + idn,
        capability_mode: "read-only",
        output_schema: patch_schema,
    });
    pi += 1;
}
let patch_results = parallel(pjobs);

let patches = [];
for pr in patch_results {
    if pr != () && pr.success && pr.output.diff != () && pr.output.diff != "" {
        patches.push(pr.output);
    }
}

let report = "";
report += "# Find-patch loop\n\nConfirmed: ";
report += confirmed.len().to_string();
report += " / raw ";
report += findings.len().to_string();
report += "\nProposed patches: ";
report += patches.len().to_string();
report += "\n\nDoes not land commits. Operator applies diffs after review.\n";
let report_path = write_scratch_file("find-patch-report.md", report);

complete(#{
    summary: confirmed.len().to_string() + " confirmed, " + patches.len().to_string() + " proposed patches",
    confirmed: confirmed,
    patches: patches,
    path: report_path,
});
