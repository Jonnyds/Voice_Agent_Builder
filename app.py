"""Voice Agent Builder — Gradio single-page app.
Left: chat to build the agent. Right: the generated agent + a REAL in-browser
voice call powered by Vapi's web SDK.

Run:  python app.py   ->  opens http://127.0.0.1:7860
"""
import os
import json
import html
import gradio as gr
from dotenv import load_dotenv

import builder

load_dotenv()

VAPI_PUBLIC_KEY = os.environ.get("VAPI_PUBLIC_KEY", "")
VOICE_PROVIDER = os.environ.get("VOICE_PROVIDER", "anthropic")
VOICE_MODEL = os.environ.get("VOICE_MODEL", os.environ.get("BUILDER_MODEL", "claude-sonnet-4-6"))

HEAD = """
<script type="module">
  import Vapi from "https://esm.sh/@vapi-ai/web@2";
  window.__vapi = null;

  // Escape untrusted strings before inserting into the DOM (prevents HTML/JS injection).
  const esc = (s) => { const d = document.createElement("div"); d.textContent = (s == null ? "" : String(s)); return d.innerHTML; };

  window.startVapiCall = (publicKey, configJson, voiceProvider, voiceModel) => {
    const log = document.getElementById("call-log");
    const setStatus = (t) => { document.getElementById("call-status").textContent = t; };
    if (!publicKey) { alert("Enter your Vapi PUBLIC key first."); return; }
    let cfg;
    try { cfg = JSON.parse(configJson); }
    catch (e) { alert("No valid agent yet — build one first."); return; }

    log.innerHTML = "";
    const vapi = new Vapi(publicKey.trim());
    window.__vapi = vapi;

    vapi.on("call-start", () => setStatus("🟢 connected — start talking"));
    vapi.on("call-end",   () => setStatus("call ended"));
    vapi.on("error", (e) => {
      const inner = e?.error || e;
      const msg = inner?.message || JSON.stringify(inner, Object.getOwnPropertyNames(inner || {}));
      console.error("Vapi error:", e);
      setStatus("error: " + msg);
    });
    vapi.on("message", (m) => {
      if (m.type === "transcript" && m.transcriptType === "final") {
        const who = m.role === "assistant" ? cfg.name : "You";
        const d = document.createElement("div");
        d.style.cssText = "margin:6px 0;padding:8px 12px;border-radius:10px;max-width:88%;font-size:14px;line-height:1.5;" +
          (m.role === "assistant" ? "background:#fff;border:1px solid #e4e2db;" : "background:#14161f;color:#fff;margin-left:auto;");
        // esc() prevents any script/markup in the name or transcript from executing.
        d.innerHTML = "<b style='font-size:11px;opacity:.6;display:block'>" + esc(who) + "</b>" + esc(m.transcript);
        log.appendChild(d); log.scrollTop = log.scrollHeight;
      }
      if (m.type === "tool-calls" || m.type === "function-call") {
        const call = (m.toolCalls || (m.functionCall ? [m.functionCall] : [])).find(Boolean);
        if (call) {
          const args = call.function?.arguments || call.parameters || {};
          const d = document.createElement("div");
          d.style.cssText = "margin:6px 0;padding:8px 12px;border-radius:10px;background:#eaf6ee;border:1px solid #cfe8d6;font-size:13px;";
          d.textContent = "📅 BOOKING: " + JSON.stringify(args);  // textContent = safe by default
          log.appendChild(d); log.scrollTop = log.scrollHeight;
        }
      }
    });

    setStatus("connecting…");
    vapi.start({
      firstMessage: cfg.firstMessage,
      model: {
        provider: voiceProvider,
        model: voiceModel,
        messages: [{ role: "system", content: cfg.systemPrompt }],
        tools: [{
          type: "function",
          function: {
            name: "book_meeting",
            description: "Call this when the lead qualifies and gives a preferred time.",
            parameters: {
              type: "object",
              properties: {
                name: { type: "string", description: "the lead's name" },
                preferredTime: { type: "string", description: "e.g. 'Thursday 2pm'" }
              },
              required: ["preferredTime"]
            }
          }
        }]
      }
    }).then(() => {
      setStatus("🟢 call starting…");
    }).catch((e) => {
      const inner = e?.error || e;
      const msg = inner?.message || JSON.stringify(inner, Object.getOwnPropertyNames(inner || {}));
      console.error("start failed:", e);
      setStatus("start failed: " + msg);
    });
  };

  window.stopVapiCall = () => { if (window.__vapi) window.__vapi.stop(); };
</script>
"""

CSS = """
#agent-box { background:#fff; border:1px solid #e4e2db; border-radius:12px; padding:14px; }
#call-log { min-height:120px; max-height:280px; overflow-y:auto; display:flex; flex-direction:column; margin-top:8px; }
.chip { background:#edecfb; color:#5b5bd6; border-radius:999px; padding:3px 10px; font-size:12px; font-weight:600; }
footer { display:none !important; }
"""


def respond(message, chat_history, config_state):
    if not message.strip():
        return chat_history, config_state, render_agent(config_state), config_json(config_state)

    pairs = [(m["role"], m["content"]) for m in chat_history] + [("user", message)]
    chat_history = chat_history + [{"role": "user", "content": message}]

    try:
        kind, payload = builder.build_agent(pairs, config_state)
        if kind == "build":
            config_state = payload
            reply = f'Built "{payload["name"]}". See it on the right — then start a call.'
        else:  # clarify or refuse — payload is already the text to show
            reply = payload
    except Exception as e:
        reply = f"Error: {e}"

    chat_history = chat_history + [{"role": "assistant", "content": reply}]
    return chat_history, config_state, render_agent(config_state), config_json(config_state)


def render_agent(cfg):
    if not cfg:
        return "<div id='agent-box'><span class='chip'>Your agent</span><p style='color:#6b6a64'>Nothing built yet. Describe an agent on the left.</p></div>"
    # Escape every LLM-produced field before putting it into HTML (prevents injection).
    name = html.escape(str(cfg.get("name", "")))
    goal = html.escape(str(cfg.get("goal", "")))
    first = html.escape(str(cfg.get("firstMessage", "")))
    qs = "".join(f"<li>{html.escape(str(q))}</li>" for q in cfg.get("questions", []))
    return f"""<div id='agent-box'>
      <span class='chip'>Your agent</span>
      <h3 style='margin:10px 0 4px'>{name}</h3>
      <p style='color:#6b6a64;margin:0 0 8px'><b>Goal:</b> {goal}</p>
      <p style='font-style:italic;margin:0 0 8px'>“{first}”</p>
      <b style='font-size:12px;color:#6b6a64'>QUALIFYING QUESTIONS</b>
      <ol style='margin:4px 0 0;padding-left:20px'>{qs}</ol>
    </div>"""


def config_json(cfg):
    return json.dumps(cfg) if cfg else ""


with gr.Blocks(head=HEAD, css=CSS, title="Voice Agent Builder") as demo:
    config_state = gr.State(None)

    gr.Markdown("### ◆ Voice Agent Builder\nDescribe an agent → it gets built → talk to it live in your browser.")

    with gr.Row():
        with gr.Column():
            gr.Markdown("**1 · Builder**")
            chatbot = gr.Chatbot(type="messages", height=380, show_label=False)
            msg = gr.Textbox(placeholder="e.g. Build an agent that calls gym trial sign-ups and books a tour", show_label=False)
            gr.Examples(
                ["Build an agent that calls gym free-trial sign-ups and books a tour",
                 "Agent that calls tutoring leads, finds subject and grade, books a trial lesson"],
                inputs=msg,
            )

        with gr.Column():
            gr.Markdown("**2 · Your agent**")
            agent_html = gr.HTML(render_agent(None))
            config_box = gr.Textbox(visible=False)
            # Voice model/provider passed to the JS so nothing is hardcoded there.
            voice_provider_box = gr.Textbox(value=VOICE_PROVIDER, visible=False)
            voice_model_box = gr.Textbox(value=VOICE_MODEL, visible=False)

            gr.Markdown("**3 · Talk to your agent**")
            pubkey = gr.Textbox(label="Vapi public key (pk_…)", value=VAPI_PUBLIC_KEY, placeholder="paste your PUBLIC key")
            with gr.Row():
                start_btn = gr.Button("🎙️ Start call", variant="primary")
                stop_btn = gr.Button("End call")
            gr.HTML("<span id='call-status' style='font-size:13px;color:#6b6a64'>idle</span><div id='call-log'></div>")

    msg.submit(respond, [msg, chatbot, config_state], [chatbot, config_state, agent_html, config_box]).then(
        lambda: "", None, msg)

    start_btn.click(
        fn=None,
        inputs=[pubkey, config_box, voice_provider_box, voice_model_box],
        js="(k, c, p, m) => window.startVapiCall(k, c, p, m)",
    )
    stop_btn.click(fn=None, js="() => window.stopVapiCall()")

if __name__ == "__main__":
    demo.launch(show_api=False)