# Best Local LLM for Biblical Radio Drama

## Recommended Models

There are **no MLX models fine-tuned specifically on biblical texts** yet, but these work excellently and are now in the registry:

| Model | Tag | Why It's Great |
|-------|-----|----------------|
| **Hermes-2-Mixtral-8x7B** | `Biblical` | Best for scripture analysis. Hermes instruction tuning gives nuanced theological reasoning. MoE = strong quality at reasonable speed. |
| **Qwen3-Drama-8B** | `Drama AI` | Already fine-tuned on 6,319 drama scripts with reasoning chains. Thinks through character psychology and structure before writing. |
| **Mistral-Nemo-12B** | `128K Ctx` | 128K context window handles entire books of the Bible in one pass. Strong dialogue and character voice. |
| **Hermes-3-Llama-8B** | `Scripture` | Compact option that runs on 8GB. Good starting point for scripture-to-drama. |

**Recommended stack for biblical drama:** Use **Hermes-2-Mixtral-8x7B** for analysis/exegesis, then **Qwen3-Drama-8B** for script generation.

---

## How to Customize an MLX Model for Creative Writing

The best approach is **LoRA fine-tuning** via `mlx-lm`. A complete guide is also available in the Models page of the web UI (collapsible section at the bottom).

### Step 1: Prepare Training Data

Create 300-500 examples of (biblical passage -> radio drama script) in chat JSONL format.

Create `train.jsonl` and `valid.jsonl` files:

```json
{"messages": [
  {"role": "system", "content": "You are a radio drama scriptwriter specializing in biblical adaptations."},
  {"role": "user", "content": "Convert Genesis 22:1-14 (The Binding of Isaac) into a radio drama scene."},
  {"role": "assistant", "content": "[MUSIC: Ancient strings, somber]\n\nNARRATOR: (gravely) And it came to pass that God tested Abraham.\n\n[SFX: Desert wind, distant sheep bleating]\n\nGOD: (thundering, echoing) Abraham!\n\nABRAHAM: (kneeling) Here I am, Lord.\n\nGOD: Take your son — your only son Isaac, whom you love — and go to Moriah.\n\n[SFX: Abraham's sharp intake of breath]\n\nNARRATOR: (hushed) Three words seared into his heart. Your only son.\n\n[MUSIC: Tension builds with low drums]"}
]}
```

### Step 2: Fine-Tune with LoRA

Works on 16GB Macs with QLoRA:

```bash
# Install mlx-lm
pip install mlx-lm

# Fine-tune (QLoRA)
mlx_lm.lora \
  --model mlx-community/Qwen3-8B-4bit \
  --data ./radio_drama_data \
  --train \
  --batch-size 2 \
  --iters 600 \
  --num-layers 16 \
  --mask-prompt \
  --grad-checkpoint \
  --adapter-path ./adapters/biblical_drama
```

**Key flags:**
- `--mask-prompt` — learns output style (not input memorization)
- `--grad-checkpoint` — reduces memory usage
- `--num-layers 16` — balances quality vs. speed

### Step 3: Test Your Adapter

```bash
# Generate with adapter (base model + adapter loaded separately)
mlx_lm.generate \
  --model mlx-community/Qwen3-8B-4bit \
  --adapter-path ./adapters/biblical_drama \
  --prompt "Convert Psalm 23 into a radio drama scene with narrator and voices." \
  --max-tokens 1024

# Fuse adapter permanently into a new model
mlx_lm.fuse \
  --model mlx-community/Qwen3-8B-4bit \
  --adapter-path ./adapters/biblical_drama \
  --save-path ./models/biblical-drama-qwen3-8b
```

---

## Recommended Base Models for Fine-Tuning

| Model | RAM | Best For |
|-------|-----|----------|
| **Qwen3-8B-4bit** | ~7 GB | Best post-fine-tune quality. Already has a drama variant (Qwen3-8B-Drama-Thinking). |
| **Mistral-Nemo-12B-4bit** | ~8 GB | 128K context. Popular creative-writing base. Strong narrative + character voices. |
| **Llama-3.1-8B-4bit** | ~6 GB | Greatest improvement from LoRA. Huge community ecosystem. |
| **Hermes-2-Mixtral-8x7B-4bit** | ~26 GB | Best for biblical/theological analysis. Strong nuanced reasoning. |

---

## Useful Datasets

| Dataset | What |
|---------|------|
| `FutureMa/DramaBench` | 1,103 professional scripts in Fountain format. Best drama training data. |
| `aneeshas/imsdb-drama-movie-scripts` | Drama movie scripts from IMSDB. Good for dialogue style. |
| `bible-nlp/biblenlp-corpus` | Multi-language parallel Bible corpus for theological grounding. |
| `Nitral-AI/Creative_Writing-ShareGPT` | Creative writing examples in chat format. Ready for mlx-lm. |
| `euclaise/writingprompts` | ~4B tokens of creative writing from r/WritingPrompts. |

---

## Advanced LoRA Configuration

For best results, target both attention and MLP layers:

```yaml
# lora_config.yaml
model: mlx-community/Qwen3-8B-4bit
train: true
data: ./radio_drama_data
fine_tune_type: lora
batch_size: 2
iters: 600
learning_rate: 1e-5
steps_per_report: 10
steps_per_eval: 100
save_every: 200
max_seq_length: 4096
mask_prompt: true
grad_checkpoint: true

num_layers: 16
lora_parameters:
  rank: 16
  scale: 20.0
  dropout: 0.05
  keys:
    - "self_attn.q_proj"
    - "self_attn.v_proj"
    - "self_attn.k_proj"
    - "self_attn.o_proj"
    - "mlp.gate_proj"
    - "mlp.down_proj"
    - "mlp.up_proj"

adapter_path: ./adapters/radio_drama
```

Run with: `mlx_lm.lora --config lora_config.yaml`
