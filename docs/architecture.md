# TraceMap — Architecture

## Diagram 1 — How CodeMap turns a traceback into evidence

```mermaid
flowchart TD
    A([raw traceback text]) --> B["parse_trace(text)"]
    B --> C[list of Frame objects]
    C --> D["build_index(path)"]
    D --> E["CodeIndex<br/>_source_files + resolve_calls"]
    C --> F["map_frames(index, frames)"]
    E --> F
    F --> G["matched Symbol"]
    G --> H["CodeIndex.incoming(symbol_id)"]
    G --> I["CodeIndex.outgoing(symbol_id)"]
    H --> J["callers"]
    I --> K["callees"]
    G --> L["CodeIndex.transitive_callers(symbol_id)"]
    L --> M["blast radius — BFS shallowest-first"]
    M --> N["filter _is_test_symbol"]
    N --> O(["covering tests"])
```

Each frame in the raw traceback is resolved to an indexed `Symbol` by `map_frames()`, then CodeMap's graph queries expose the full caller/callee web and blast radius so nothing relevant to the crash is overlooked.

---

## Diagram 2 — TraceMap end to end

```mermaid
flowchart LR
    subgraph TM ["TraceMap — harness"]
        T1([crash / traceback])
        T2[call CodeMap API]
        T3[assemble evidence pack]
        T4[run affected tests]
        T5([proof artifact])
    end

    subgraph CM ["CodeMap — deterministic"]
        C1["parse_trace + map_frames"]
        C2["build_index"]
        C3["transitive_callers"]
        C4["affected_tests"]
    end

    subgraph BOB ["IBM Bob — reasoning"]
        B1["read evidence pack<br/>Agent mode"]
        B2["write fix patch"]
        B3["write regression test"]
        B4["iterate on test failures"]
    end

    T1 --> T2
    T2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> T3
    T3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> T4
    T4 --> T5
```

The crash flows left-to-right through three clearly separated actors: CodeMap deterministically maps the evidence (no LLM guessing), IBM Bob reasons over that evidence to write a fix and a regression test, and the TraceMap harness orchestrates the handoffs and verifies the fail-before / pass-after proof.
