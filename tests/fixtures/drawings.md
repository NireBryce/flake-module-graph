# Drawings kept current

`checks.markdown` in flake.nix runs `lib.checkMarkdown` on this file: a
drawing here that no longer matches tests/fixtures/golden.json fails it.
Redraw with `python3 -m module_graph markdown tests/fixtures/golden.json
--config tests/fixtures/golden.toml --file tests/fixtures/drawings.md`.

<!-- module-graph: tree --depth 1 --categories-only -->
```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "ui-sans-serif, system-ui, sans-serif", "fontSize": "14px", "lineColor": "#94a3b8"}, "flowchart": {"curve": "basis", "nodeSpacing": 24, "rankSpacing": 80, "padding": 14}}}%%
flowchart LR
    subgraph g0["users"]
        n12("<b>shell/</b><br/><i>h · 1</i>")
    end
    subgraph g1["shared"]
        n6("<b>base/</b><br/><i>n h d · 3</i>")
        n7("<b>desktop/</b><br/><i>n h · 3</i>")
        n8("<b>extras/</b><br/><i>n · 2</i>")
        n9("<b>fonts/</b><br/><i>n · 1</i>")
        n10("<b>lonely/</b><br/><i>n · 1</i>")
        n11("<b>printing/</b><br/><i>n · 1</i>")
    end
    subgraph g2["hosts-config"]
        n5("<b>laptop/</b><br/><i>n · 1</i>")
    end
    style g0 fill:#f8fafc,stroke:#cbd5e1,color:#64748b
    style g1 fill:#f8fafc,stroke:#cbd5e1,color:#64748b
    style g2 fill:#f8fafc,stroke:#cbd5e1,color:#64748b
    classDef area fill:#f8fafc,stroke:#cbd5e1,color:#1e293b,stroke-width:1.5px
    classDef category fill:#dbeafe,stroke:#2563eb,color:#1e293b,stroke-width:1.5px
    classDef folder fill:#f1f5f9,stroke:#94a3b8,color:#1e293b,stroke-width:1.5px
    classDef module fill:#ffffff,stroke:#94a3b8,color:#1e293b,stroke-width:1.5px
    classDef aggregate fill:#ffffff,stroke:#f59e0b,color:#1e293b,stroke-width:1.5px
    classDef missing fill:#fee2e2,stroke:#ef4444,color:#1e293b,stroke-width:1.5px
    classDef orphan fill:#fff1f2,stroke:#e11d48,color:#1e293b,stroke-width:2.5px
    classDef bymodule stroke-dasharray:5 3
    class n5,n6,n7,n8,n9,n10,n11,n12 category
    class n8 bymodule
    class n10 orphan
```
<!-- /module-graph -->

<!-- module-graph: hosts --category base -->
```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "ui-sans-serif, system-ui, sans-serif", "fontSize": "14px", "lineColor": "#94a3b8"}, "flowchart": {"curve": "basis", "nodeSpacing": 24, "rankSpacing": 80, "padding": 14}}}%%
flowchart TB
    subgraph g0["hosts and home"]
        n2[["<b>laptop-host</b><br/><i>nixos</i>"]]
        n3[["<b>mac</b><br/><i>darwin</i>"]]
        n4[["<b>server</b><br/><i>nixos</i>"]]
    end
    n0("<b>base/</b><br/><i>n h d · 3</i>")
    n1("<b>net/</b><br/><i>n h · 1</i>")
    n2 --> n0
    n3 --> n0
    n4 --> n0
    linkStyle 0 stroke:#16a34a,stroke-width:1.5px
    linkStyle 1 stroke:#d97706,stroke-width:1.5px
    linkStyle 2 stroke:#9333ea,stroke-width:1.5px
    style g0 fill:#fefce8,stroke:#fde68a,color:#64748b
    style n2 stroke:#16a34a,stroke-width:2px
    style n3 stroke:#d97706,stroke-width:2px
    style n4 stroke:#9333ea,stroke-width:2px
    classDef area fill:#f8fafc,stroke:#cbd5e1,color:#1e293b,stroke-width:1.5px
    classDef category fill:#dbeafe,stroke:#2563eb,color:#1e293b,stroke-width:1.5px
    classDef folder fill:#f1f5f9,stroke:#94a3b8,color:#1e293b,stroke-width:1.5px
    classDef module fill:#ffffff,stroke:#94a3b8,color:#1e293b,stroke-width:1.5px
    classDef aggregate fill:#ffffff,stroke:#f59e0b,color:#1e293b,stroke-width:1.5px
    classDef missing fill:#fee2e2,stroke:#ef4444,color:#1e293b,stroke-width:1.5px
    classDef orphan fill:#fff1f2,stroke:#e11d48,color:#1e293b,stroke-width:2.5px
    classDef bymodule stroke-dasharray:5 3
    class n0,n1 category
    class n2,n3,n4 aggregate
```
<!-- /module-graph -->
