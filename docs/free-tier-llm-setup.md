# Free-tier LLM setup

Bounty Servant's current daily radar does not need an LLM. This adapter adds an optional, dependency-free way for later code-review and patch-planning steps to call a free-tier model.

## Recommended: Google Gemini API

1. Open https://aistudio.google.com/ and create an API key.
2. In the GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Name the secret `GEMINI_API_KEY` and paste the key as its value.
4. Optionally set `GEMINI_MODEL` as an Actions variable. The default is `gemini-2.5-flash`; confirm the model is currently available to your account.
5. Keep the secret out of source files, issue comments, workflow logs, and artifacts.

## Optional fallback: Groq

1. Create a key at https://console.groq.com/.
2. Add a repository secret named `GROQ_API_KEY`.
3. The default model is `llama-3.3-70b-versatile`. Set `GROQ_MODEL` as an Actions variable if that model is unavailable.

## Provider selection

- `BOUNTY_LLM_PROVIDER=auto`: try Gemini, then Groq if configured.
- `BOUNTY_LLM_PROVIDER=gemini`: use Gemini only.
- `BOUNTY_LLM_PROVIDER=groq`: use Groq only.

The adapter uses only Python's standard library. Run tests with:

```sh
python -m unittest discover -s tests -v
```

## Safety and limitations

This adapter only sends prompts and returns generated text. It does not clone repositories, execute generated code, post comments, push branches, or open pull requests. Those actions must be implemented as a separate guarded workflow with sandboxed execution, explicit test checks, and least-privilege permissions.

Free quotas, available models, and provider terms can change. Do not send private or sensitive repository content unless the provider's current terms and your authorization permit it.
