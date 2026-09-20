# S1 Manual Paired-Trajectory Review Evidence

**Artifact provenance: ORIGINAL SAVED ARTIFACT**

This packet contains only selected step directories copied byte-for-byte from
the already saved P0 and S1 runtimes. The JSON files were not rewritten,
redacted, or re-serialized. Each excerpt retains the original actor input and
prompt, raw and parsed response, action validation, environment result, step
record, and usage/error artifacts present at that step.

No model/API call was made while assembling this packet. The complete runtimes
remain locally available at:

```text
artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1
artifacts/exploratory_memory_mvp/stronger-actor-s1-qwen38max-20260920-4c3d413
```

The packet is intentionally small: 30 selected step directories rather than
the full P0/S1 trajectories. Every directory below is an **ORIGINAL SAVED
ARTIFACT** excerpt; the destination name is only a review label.

## Excerpt mapping

| Packet directory | Original saved step artifact |
| --- | --- |
| `laptop_p0_step02` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/000_db485ebd50e7/P0/steps/002` |
| `laptop_s1_step02` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/000_db485ebd50e7/S1/steps/002` |
| `soap_p0_step03` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/001_4d0e4849f544/P0/steps/003` |
| `soap_s1_step03` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/001_4d0e4849f544/S1/steps/003` |
| `soap_p0_step31` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/001_4d0e4849f544/P0/steps/031` |
| `soap_p0_step32` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/001_4d0e4849f544/P0/steps/032` |
| `soap_s1_step11` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/001_4d0e4849f544/S1/steps/011` |
| `soap_s1_step12` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/001_4d0e4849f544/S1/steps/012` |
| `soap_s1_step17` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/001_4d0e4849f544/S1/steps/017` |
| `soap_s1_step18` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/001_4d0e4849f544/S1/steps/018` |
| `apple_p0_step01` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/002_9fa5d3902fe0/P0/steps/001` |
| `apple_s1_step01` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/002_9fa5d3902fe0/S1/steps/001` |
| `apple_p0_step12` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/002_9fa5d3902fe0/P0/steps/012` |
| `apple_p0_step18` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/002_9fa5d3902fe0/P0/steps/018` |
| `apple_s1_step07` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/002_9fa5d3902fe0/S1/steps/007` |
| `apple_s1_step08` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/002_9fa5d3902fe0/S1/steps/008` |
| `apple_s1_step20` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/002_9fa5d3902fe0/S1/steps/020` |
| `apple_s1_step21` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/002_9fa5d3902fe0/S1/steps/021` |
| `shelf_p0_step01` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/003_a04b6f263f6d/P0/steps/001` |
| `shelf_s1_step01` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/003_a04b6f263f6d/S1/steps/001` |
| `shelf_p0_step18` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/003_a04b6f263f6d/P0/steps/018` |
| `shelf_p0_step20` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/003_a04b6f263f6d/P0/steps/020` |
| `shelf_s1_step02` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/003_a04b6f263f6d/S1/steps/002` |
| `shelf_s1_step03` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/003_a04b6f263f6d/S1/steps/003` |
| `shelf_s1_step05` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/003_a04b6f263f6d/S1/steps/005` |
| `shelf_s1_step07` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/003_a04b6f263f6d/S1/steps/007` |
| `coffee_p0_step02` | `paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1/tasks/004_6cf8b7e81791/P0/steps/002` |
| `coffee_s1_step02` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/004_6cf8b7e81791/S1/steps/002` |
| `coffee_s1_step03` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/004_6cf8b7e81791/S1/steps/003` |
| `coffee_s1_step04` | `stronger-actor-s1-qwen38max-20260920-4c3d413/tasks/004_6cf8b7e81791/S1/steps/004` |

The packet contains no new evaluator labels, oracle routes, target metadata,
or reviewer-generated fields inside the copied runtime JSON.
