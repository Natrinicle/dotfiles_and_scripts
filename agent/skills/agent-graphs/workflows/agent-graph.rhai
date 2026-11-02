let meta = #{
    name: "agent-graph",
    description: "Split independent units, run isolated workers, gate each unit, return failures only",
    when_to_use: "multi-agent graph, fan-out workers, loop until green, blast-radius gate, independent units in parallel",
    phases: [
        #{ title: "Split", detail: "cut work into units if not already listed" },
        #{ title: "Work", detail: "one isolated worker per unit" },
        #{ title: "Gate", detail: "independent checker per unit against a programmable check" },
    ],
};

let units_schema = #{
    "type": "object", "required": ["units"],
    "properties": #{
        "units": #{ "type": "array", "maxItems": 8, "items": #{
            "type": "object",
            "required": ["id", "brief"],
            "properties": #{
                "id": #{ "type": "string" },
                "brief": #{ "type": "string" },
            },
        }},
    },
};
let work_schema = #{
    "type": "object", "required": ["id", "status", "summary", "evidence"],
    "properties": #{
        "id": #{ "type": "string" },
        "status": #{ "type": "string", "enum": ["done", "blocked"] },
        "summary": #{ "type": "string" },
        "evidence": #{ "type": "string" },
    },
};
let gate_schema = #{
    "type": "object", "required": ["id", "verdict", "reason", "evidence", "scope"],
    "properties": #{
        "id": #{ "type": "string" },
        "verdict": #{ "type": "string", "enum": ["green", "red", "unverified"] },
        "reason": #{ "type": "string" },
        "evidence": #{ "type": "string" },
        "scope": #{ "type": "string" },
    },
};

let task = if args == () { () } else { args.task };
let check_text = if args == () { () } else { args.check };
let units_in = if args == () { () } else { args.units };
if task == () || check_text == () {
    pause("verification", "Pass args.task and args.check (a programmable green condition). Optional args.units is an array of independent unit strings.");
}

let task_json = json_encode(task);
let check_json = json_encode(check_text);

let units = [];
if units_in != () && type_of(units_in) == "array" {
    let ui = 0;
    for u in units_in {
        if units.len() >= 8 {
            log("dropped extra pre-split units past cap 8");
            break;
        }
        if type_of(u) == "string" && u != "" {
            let n = ui + 1;
            let idn = if n < 10 { "U-0" + n.to_string() } else { "U-" + n.to_string() };
            units.push(#{ id: idn, brief: u });
            ui += 1;
        }
    }
}

if units.len() == 0 {
    phase("Split");
    let sp = "";
    sp += "You are a splitter. Cut this task into independent units. Task: ";
    sp += task_json;
    sp += " Green check for each unit: ";
    sp += check_json;
    sp += " An edge exists only when the next unit must read a named output from the previous. ";
    sp += "Delete fake and-then edges. Each unit is one bounded job, one lens. ";
    sp += "Use read_file/grep if the task names a tree. Return at most 8 units as {id, brief}. ";
    sp += "id like U-01. An empty list is valid only after you inspected the task.";
    let split_r = agent(sp, #{
        label: "splitter",
        capability_mode: "read-only",
        output_schema: units_schema,
    });
    if split_r == () || !split_r.success || split_r.output.units == () {
        complete(#{ summary: "Splitter failed; unverified.", accepted: [], returned: [] });
    }
    for u in split_r.output.units {
        if units.len() >= 8 {
            log("dropped extra splitter units past cap 8");
            break;
        }
        if u.id != () && u.brief != () && u.brief != "" {
            units.push(u);
        }
    }
}

if units.len() == 0 {
    complete(#{ summary: "No units.", accepted: [], returned: [] });
}
log(units.len().to_string() + " units");

phase("Work");
let wjobs = [];
for u in units {
    let ujson = json_encode(u);
    let wp = "";
    wp += "You are one worker on one unit. You do not see sibling units. Task: ";
    wp += task_json;
    wp += " Unit: ";
    wp += ujson;
    wp += " Programmable check (you may run it, you may not grade yourself as done): ";
    wp += check_json;
    wp += " Use tools (read_file, grep, shell) on this unit only. Do not commit. Do not expand scope. ";
    wp += "Return {id, status, summary, evidence}. id must match the unit id. ";
    wp += "evidence must be command output or file paths you collected. status=blocked if you cannot run.";
    wjobs.push(#{
        prompt: wp,
        label: "worker:" + u.id,
        capability_mode: "execute",
        output_schema: work_schema,
    });
}
let work_results = parallel(wjobs);

let works = [];
let work_failed = 0;
let wi = 0;
for wr in work_results {
    if wr == () || !wr.success {
        work_failed += 1;
        works.push(#{
            id: units[wi].id,
            status: "blocked",
            summary: "worker slot failed",
            evidence: "",
            brief: units[wi].brief,
        });
    } else {
        let wout = wr.output;
        works.push(#{
            id: wout.id,
            status: wout.status,
            summary: wout.summary,
            evidence: wout.evidence,
            brief: units[wi].brief,
        });
    }
    wi += 1;
}
log(works.len().to_string() + " worker results; " + work_failed.to_string() + " slots failed");

phase("Gate");
let gjobs = [];
for w in works {
    let wjson = json_encode(w);
    let gp = "";
    gp += "You are an independent gate. You did not produce this unit. Try to fail the check. Task: ";
    gp += task_json;
    gp += " Green condition: ";
    gp += check_json;
    gp += " Worker output: ";
    gp += wjson;
    gp += " Re-run the check with tools. verdict=green only with command output you collected. ";
    gp += "If you cannot run the check, verdict=unverified. Do not produce a replacement unit. ";
    gp += "Return {id, verdict, reason, evidence, scope}. id must match the unit. ";
    gp += "scope is what a correction may touch (this unit only).";
    gjobs.push(#{
        prompt: gp,
        label: "gate:" + w.id,
        capability_mode: "execute",
        output_schema: gate_schema,
    });
}
let gate_results = parallel(gjobs);

let accepted = [];
let returned = [];
let gate_failed = 0;
let gi = 0;
for gr in gate_results {
    if gr == () || !gr.success {
        gate_failed += 1;
        returned.push(#{
            id: works[gi].id,
            verdict: "unverified",
            reason: "gate slot failed",
            evidence: "",
            scope: "this unit only",
        });
    } else if gr.output.verdict == "green"
        && gr.output.evidence != () && gr.output.evidence != "" {
        accepted.push(gr.output);
    } else {
        returned.push(gr.output);
    }
    gi += 1;
}

let report = "";
report += "# Agent graph\n\nAccepted: ";
report += accepted.len().to_string();
report += " / units ";
report += units.len().to_string();
report += "\nReturned (red or unverified): ";
report += returned.len().to_string();
report += "\nWorker slots failed: ";
report += work_failed.to_string();
report += "\nGate slots failed: ";
report += gate_failed.to_string();
report += "\n\nDoes not land commits. Return the unit, not the batch. Correction cap is three on the parent loop.\n";
let report_path = write_scratch_file("agent-graph-report.md", report);

complete(#{
    summary: accepted.len().to_string() + " accepted, " + returned.len().to_string() + " returned",
    accepted: accepted,
    returned: returned,
    path: report_path,
});
