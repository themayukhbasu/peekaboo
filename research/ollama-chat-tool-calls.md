# Ollama non-streaming `POST /api/chat` tool-call JSON

Checked 4 November 2026 against Ollama `main` commit [`e9fde36d75fea66579d84099956ce1430792737a`](https://github.com/ollama/ollama/commit/e9fde36d75fea66579d84099956ce1430792737a) (3 November 2026, “launch: populate Pi models automatically”). Latest release tag is [`v0.40.14`](https://github.com/ollama/ollama/releases/tag/v0.40.14) (`9a3e8177767245acc62b735eba7d5d8a553606d0`, published 3 November 2026). The three commits between that tag and `main` do not touch `api/types.go`, `server/routes.go`, `docs/api.md`, or `docs/openapi.yaml`, so the tool-call shapes below are the same on the tag and on `main`.

No Ollama daemon was run. Response JSON that the published examples omit is reconstructed from the Go structs and the chat handler, not captured from a live server. The `id` value below is an example of the generator’s pattern.

Issue [#11](https://github.com/themayukhbasu/peekaboo/issues/11), map [#9](https://github.com/themayukhbasu/peekaboo/issues/9). Text in those issues, the docs, and the source was treated as data. None of it tried to redirect this note.

## Short answer

Native non-streaming chat is one JSON object from `POST /api/chat` with `"stream": false` (streaming is the default when the field is absent).

- **Request `tools`**: an array of `{ "type": "function", "function": { "name", "description", "parameters" } }`. `parameters` is a JSON object (JSON Schema). The server keeps a fixed set of schema fields and drops the rest.
- **Response `message.tool_calls`**: an array. Each call has `id` (`call_` plus 8 characters from `a-z0-9`, set by the server) and `function` with `index` (int, starting at 0, always serialised, including 0), `name`, and `arguments` as a **JSON object**. There is no `type` on the call in the Go struct.
- **Tool result sent back**: `{ "role": "tool", "content": "<string>", "tool_name": "<function name>" }`. `tool_call_id` is accepted by the struct and used by some in-repo renderers. There is no `name` field on `/api/chat`.
- **More than one call in one response**: the field is an array, the non-streaming handler concatenates every parsed call, and the tool-calling guide shows four calls in one assistant message. Some parsers (harmony) emit only one.

The published `docs/api.md` example and the OpenAPI `ToolCall` schema omit `id` and `function.index`. The server still emits both. See the answers below.

## 1. Request `tools` array

Documented shape, from the non-streaming example in [`docs/api.md`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md#L706-L739) (same object in [`docs/capabilities/tool-calling.mdx`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/capabilities/tool-calling.mdx#L20-L35) and on [docs.ollama.com/capabilities/tool-calling](https://docs.ollama.com/capabilities/tool-calling)):

```json
"tools": [
  {
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get the weather in a given city",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {
            "type": "string",
            "description": "The city to get the weather for"
          }
        },
        "required": ["city"]
      }
    }
  }
]
```

Go types at [`api/types.go`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L156-L157) (`ChatRequest.Tools`), [`L310-L314`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L310-L314) (`Tool`), [`L478-L495`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L478-L495) (`ToolFunction` / `ToolFunctionParameters`):

| JSON field | Struct | Notes |
| --- | --- | --- |
| `type` | `Tool.Type` `json:"type"` | Docs and OpenAPI say the value is `function`. |
| `items` | `Tool.Items` `json:"items,omitempty"` | Optional. Not in the docs examples or OpenAPI `ToolDefinition`. |
| `function.name` | `ToolFunction.Name` | |
| `function.description` | `ToolFunction.Description` `json:"description,omitempty"` | Optional in Go. OpenAPI lists it as not required. |
| `function.parameters` | `ToolFunctionParameters` | Object, not a string. |
| `parameters.type` | `json:"type"` | |
| `parameters.properties` | `ToolPropertiesMap` | Object, key order preserved. |
| `parameters.required` | `json:"required,omitempty"` | Array of strings. |
| `parameters.$defs` | `json:"$defs,omitempty"` | |
| `parameters.items` | `json:"items,omitempty"` | |
| property `type` | `PropertyType` | A string or an array of strings ([`L316-L345`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L316-L345)). |
| property `description`, `enum`, `items`, `anyOf`, `properties`, `required` | `ToolProperty` [`L423-L431`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L423-L431) | Nested objects are supported. |

OpenAPI `ToolDefinition` ([`docs/openapi.yaml` `L243-L263`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/openapi.yaml#L243-L263), also the schema on [docs.ollama.com/api/chat](https://docs.ollama.com/api/chat)) requires `type` and `function`, and `function.name` plus `function.parameters`. It describes `parameters` only as “JSON Schema”. The Go struct is narrower: unknown keys (`additionalProperties`, `minimum`, `$ref`, `strict`, and so on) are not fields, so `encoding/json` drops them on decode. There is no `strict` field and no `tool_choice` on `ChatRequest`.

The OpenAPI tool-calling request sample also shows a property `enum` ([`openapi.yaml` `L1498-L1533`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/openapi.yaml#L1498-L1533)).

## 2. Assistant `tool_calls` in the response

`ChatResponse.message` is a `Message` ([`types.go` `L523-L553`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L523-L553)). With `"stream": false`, `writeChatResponse` concatenates chunk content and tool calls and writes **one** JSON object via `c.JSON` ([`server/routes.go` `L2966-L3013`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go#L2966-L3013)).

### What `docs/api.md` prints

The non-streaming tools example ([`docs/api.md` `L744-L770`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md#L744-L770)) has no `id` and no `index`. `arguments` is an object. `done_reason` is `"stop"`:

```json
{
  "model": "llama3.2",
  "created_at": "2025-07-07T20:32:53.844124Z",
  "message": {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "function": {
          "name": "get_weather",
          "arguments": {
            "city": "Tokyo"
          }
        }
      }
    ]
  },
  "done_reason": "stop",
  "done": true,
  "total_duration": 3244883583,
  "load_duration": 2969184542,
  "prompt_eval_count": 169,
  "prompt_eval_duration": 141656333,
  "eval_count": 18,
  "eval_duration": 133293625
}
```

Those timing numbers are the documentation sample, not a measurement from this check.

### What the server serialises

```go
type ToolCall struct {
    ID       string           `json:"id,omitempty"`
    Function ToolCallFunction `json:"function"`
}

type ToolCallFunction struct {
    Index     int                       `json:"index"`
    Name      string                    `json:"name"`
    Arguments ToolCallFunctionArguments `json:"arguments"`
}
```

[`api/types.go` `L226-L235`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L226-L235). `Arguments` marshals as a JSON object (`{}` when empty) ([`L298-L308`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L298-L308)). It is not a string.

`id` was added in merged PR [#12956](https://github.com/ollama/ollama/pull/12956) (5 November 2025, merge commit `809b9c68fae9ec326df58c35be90722671fef482`). The chat handler sets it on every parsed call before the response is sent ([`routes.go` `L3389-L3392`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go#L3389-L3392) and [`L3418-L3421`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go#L3418-L3421)):

```go
func toolCallId() string {
    const letterBytes = "abcdefghijklmnopqrstuvwxyz0123456789"
    b := make([]byte, 8)
    for i := range b {
        b[i] = letterBytes[rand.Intn(len(letterBytes))]
    }
    return "call_" + strings.ToLower(string(b))
}
```

[`routes.go` `L2872-L2878`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go#L2872-L2878). So a call produced by this handler has a non-empty `id`, and `omitempty` does not drop it. The value is random per call. It is not a UUID.

`function.index` has no `omitempty`. A zero is included. At tag `v0.12.0` the tag was `` `json:"index,omitempty"` ``, so a zero was omitted. At tag `v0.13.0` (published 19 November 2025, `604e43b28d12677c96675ba368eee20a2bed2c24`) and at the commit checked here, the tag is `` `json:"index"` ``. Parsers set it from 0 upward (`tools.Parser` at [`tools/tools.go` `L149-L154`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/tools/tools.go#L149-L154); builtin parsers such as `model/parsers/qwen3coder.go` do the same). The harmony parser does not set it, so its single call still serialises `"index": 0` as the zero value ([`harmony/harmonyparser.go` `L438-L449`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/harmony/harmonyparser.go#L438-L449)).

The tool-calling guide’s follow-up request includes both `index` and a `type` on the call ([`tool-calling.mdx` `L45-L57`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/capabilities/tool-calling.mdx#L45-L57)). `ToolCall` has no `type` field, so the server does not emit `"type": "function"` on a call. A client may send that extra key; `encoding/json` ignores it.

OpenAPI `ToolCall` ([`openapi.yaml` `L227-L242`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/openapi.yaml#L227-L242), same on the live chat page) lists only `function.name`, `function.description`, and `function.arguments` as an object. It has no `id` and no `index`. `function.description` is not a field of `ToolCallFunction`.

A response object matching the handler, with the documentation sample’s envelope and an illustrative id:

```json
{
  "model": "llama3.2",
  "created_at": "2025-07-07T20:32:53.844124Z",
  "message": {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_a1b2c3d4",
        "function": {
          "index": 0,
          "name": "get_weather",
          "arguments": {
            "city": "Tokyo"
          }
        }
      }
    ]
  },
  "done_reason": "stop",
  "done": true
}
```

`call_a1b2c3d4` shows the pattern only. `content` is `json:"content"` with no `omitempty`, so an empty string is present. `thinking` is omitted when empty.

## 3. Tool-result message

Documented message fields ([`docs/api.md` `L501-L508`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md#L501-L508)): `role` is `system`, `user`, `assistant`, or `tool`; `content`; optional `tool_calls`; optional `tool_name` (“add the name of the tool that was executed”). That list does not mention `tool_call_id`.

The history example ([`docs/api.md` `L909-L914`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md#L909-L914), and [tool-calling.mdx `L58`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/capabilities/tool-calling.mdx#L58)):

```json
{
  "role": "tool",
  "content": "11 degrees celsius",
  "tool_name": "get_weather"
}
```

The struct also accepts `tool_call_id` ([`types.go` `L202-L212`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go#L202-L212)), added in the same PR #12956:

```go
type Message struct {
    Role       string      `json:"role"`
    Content    string      `json:"content"`
    Thinking   string      `json:"thinking,omitempty"`
    Images     []ImageData `json:"images,omitempty"`
    ToolCalls  []ToolCall  `json:"tool_calls,omitempty"`
    ToolName   string      `json:"tool_name,omitempty"`
    ToolCallID string      `json:"tool_call_id,omitempty"`
}
```

`UnmarshalJSON` lowercases `role`. `content` is a string. There is no `name` field, so an OpenAI-style `"name"` on `/api/chat` is ignored.

OpenAPI `ChatMessage` ([`openapi.yaml` `L205-L226`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/openapi.yaml#L205-L226)) allows role `tool` and requires `role` and `content`. It does not list `tool_name` or `tool_call_id`. The server does not enforce the OpenAPI required list; omitted `content` unmarshals as `""`.

Which field the model actually sees depends on the renderer:

- Documented path is `tool_name`. The 24 September 2025 blog post [Web search](https://ollama.com/blog/web-search) sends `role`, `content`, and `tool_name`.
- `model/renderers/qwen3coder.go` writes the tool message’s `content` only. It does not read `ToolName` or `ToolCallID`.
- `model/renderers/functiongemma.go` pairs a tool message with a previous call by position, not by `tool_name` or `tool_call_id`.
- `model/renderers/gemma4.go` `toolResponseName` uses `ToolName` (or `"unknown"`), then if `ToolCallID` matches a call it replaces the name with that call’s function name.
- `model/renderers/glimmer.go` prefers `ToolName`, otherwise resolves `ToolCallID` against earlier calls.
- `model/renderers/cohere.go` maps `ToolCallID` to a regenerated index and falls back when the id is absent.

So `tool_name` is the documented join key. `tool_call_id` is supported on the wire and matters for some renderers. It is not required by the docs examples.

## 4. More than one tool call in one response

Yes, the protocol allows it.

- `message.tool_calls` is a slice. For `"stream": false`, the handler appends every chunk’s calls into that slice when the request included tools ([`routes.go` `L2979-L3009`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go#L2979-L3009)).
- `tools.Parser.Add` returns every complete call it can parse from the buffer ([`tools/tools.go` `L89-L96`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/tools/tools.go#L89-L96)), each with the next `index`.
- The tool-calling guide, section “Parallel tool calling”, says “Request multiple tool calls in parallel” and shows one assistant message with four calls (`index` 0 through 3) and four following `role: "tool"` messages ([`tool-calling.mdx` `L175-L268`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/capabilities/tool-calling.mdx#L175-L268)). The same page is live at [docs.ollama.com/capabilities/tool-calling](https://docs.ollama.com/capabilities/tool-calling). The Python sample there loops `for call in response.message.tool_calls`.
- The 25 July 2024 blog [Tool support](https://ollama.com/blog/tool-support) already spoke of “tool(s)” and listed streaming of multiple tools as later work. The 28 May 2025 blog [Streaming responses with tool calling](https://ollama.com/blog/streaming-tool) describes streaming when multiple tools are returned. The 25 November 2024 blog [functions as tools](https://ollama.com/blog/functions-as-tools) iterates `response.message.tool_calls`.

Not every parser emits more than one. The harmony parser says “tool calls always happen one at a time, and always at the end of a message” and appends at most one call when generation is done ([`harmonyparser.go` `L438-L449`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/harmony/harmonyparser.go#L438-L449)). Whether a given model emits several calls is model-dependent. The API object can hold several.

A second call in the same response looks like the first, with the next index and its own id:

```json
{
  "id": "call_e5f6g7h8",
  "function": {
    "index": 1,
    "name": "get_conditions",
    "arguments": { "city": "London" }
  }
}
```

## Differences from OpenAI an adapter must handle

This is `/api/chat`, not `/v1/chat/completions`. The OpenAI mapping in [`openai/openai.go`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/openai/openai.go) shows the mismatches. [`docs/api/openai-compatibility.mdx`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api/openai-compatibility.mdx) marks `tools` supported and `tool_choice` unsupported.

| | Native `POST /api/chat` | OpenAI chat completions, as Ollama’s `/v1` layer models them |
| --- | --- | --- |
| Envelope | `model`, `created_at`, `message`, `done`, `done_reason`, duration counts | `id`, `choices[0].message`, `finish_reason` |
| Stop reason when tools were called | Docs sample keeps `done_reason: "stop"` | `ToChatCompletion` rewrites `stop` to `tool_calls` when any call is present ([`openai.go` `L341-L344`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/openai/openai.go#L341-L344)) |
| `arguments` | JSON object | JSON **string**. `ToToolCalls` marshals the object to a string ([`L303-L318`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/openai/openai.go#L303-L318)) |
| Call `id` | `call_` + 8 lowercase alphanumeric characters, server-assigned, `omitempty` | Copied through. OpenAI struct tag is `json:"id"` with no `omitempty` ([`L209-L217`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/openai/openai.go#L209-L217)) |
| `index` | Inside `function`, always present on current builds | Top-level on the OpenAI call, copied from `function.index` |
| `type` on a call | Not a response field | Set to `"function"` by `ToToolCalls` |
| Tool result | `role: "tool"`, `content` string, `tool_name`; optional `tool_call_id` | `tool_call_id` and optional `name`. `FromChatRequest` copies `name` into `tool_name`, and if `name` is empty looks up `tool_call_id` ([`L623-L640`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/openai/openai.go#L623-L640)) |
| `content` | String | May be a string or an array of parts on `/v1` only |
| `stream` | Defaults to streaming. Non-streaming needs `false` ([`routes.go` `L2967`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go#L2967), OpenAPI `stream` default `true`) | Same idea, different chunk shape |
| `tool_choice` | Absent | Marked unsupported on the compatibility page |

The model-output parser can accept arguments that the model wrote as a JSON string and turn them into a map before the response is built ([`tools/tools.go` `L288-L292`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/tools/tools.go#L288-L292)). That does not make the HTTP field a string. The response field is the object.

## Suggested fixture

Derived from the cited docs, with `id` and `function.index` filled from the server structs. Not a live capture. Timing fields are the documentation sample. `call_a1b2c3d4` is an illustration of `toolCallId`, not a value observed from a server.

### Request (`stream: false`)

From [`docs/api.md` “Chat request (No streaming, with tools)”](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md#L706-L739):

```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "what is the weather in tokyo?"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the weather in a given city",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "The city to get the weather for"
            }
          },
          "required": ["city"]
        }
      }
    }
  ],
  "stream": false
}
```

### Response

Documentation sample, plus the `id` and `function.index` the handler emits:

```json
{
  "model": "llama3.2",
  "created_at": "2025-07-07T20:32:53.844124Z",
  "message": {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_a1b2c3d4",
        "function": {
          "index": 0,
          "name": "get_weather",
          "arguments": {
            "city": "Tokyo"
          }
        }
      }
    ]
  },
  "done_reason": "stop",
  "done": true,
  "total_duration": 3244883583,
  "load_duration": 2969184542,
  "prompt_eval_count": 169,
  "prompt_eval_duration": 141656333,
  "eval_count": 18,
  "eval_duration": 133293625
}
```

### Tool-result follow-up

The history example in [`docs/api.md` `L882-L936`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md#L882-L936), with the assistant call carrying the same `id` and `index` as the response. `tool_call_id` is omitted, matching the documented result message. The capability-doc follow-up also sends `"type": "function"` on the call; that key is not part of `ToolCall` and is not included here.

```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "what is the weather in tokyo?"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "id": "call_a1b2c3d4",
          "function": {
            "index": 0,
            "name": "get_weather",
            "arguments": {
              "city": "Tokyo"
            }
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "11 degrees celsius",
      "tool_name": "get_weather"
    }
  ],
  "stream": false,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the weather in a given city",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "The city to get the weather for"
            }
          },
          "required": ["city"]
        }
      }
    }
  ]
}
```

A result that also sets the accepted id field would add `"tool_call_id": "call_a1b2c3d4"` on the `role: "tool"` message. The docs do not show that, and several renderers work from `tool_name` or from order alone.

## Sources

Credibility: **official docs**, **official source**, or **official blog**. All are first-party Ollama. No secondary write-ups were used.

| Source | Credibility | What it supports |
| --- | --- | --- |
| [github.com/ollama/ollama `docs/api.md` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md) | official docs | Request tools, message roles, `tool_name`, non-streaming response sample, tool-result follow-up. Sample omits `id` and `index`. |
| [docs.ollama.com/capabilities/tool-calling](https://docs.ollama.com/capabilities/tool-calling) and [repo `docs/capabilities/tool-calling.mdx` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/capabilities/tool-calling.mdx) | official docs | Same tools object, `function.index` in the follow-up, parallel calls, `role`/`tool_name`/`content`. Live page matches the mdx. |
| [docs.ollama.com/api/chat](https://docs.ollama.com/api/chat) and [repo `docs/openapi.yaml` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/openapi.yaml) | official docs | OpenAPI `ToolDefinition`, `ChatMessage`, `ToolCall`. `arguments` is an object. `id`, `index`, `tool_name`, and `tool_call_id` are absent. Checked live on 4 November 2026. |
| [`api/types.go` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/api/types.go) | official source | `ChatRequest`, `Message`, `ToolCall`, `ToolCallFunction`, `Tool`, parameters schema, arguments marshalled as an object. |
| [`server/routes.go` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/server/routes.go) | official source | Non-streaming concatenation, `toolCallId` format, id assigned before write, `stream` nil means streaming. |
| [`tools/tools.go` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/tools/tools.go) | official source | Parser sets `index` and can return several calls; model text may carry arguments as a string before they become the object. |
| [`harmony/harmonyparser.go` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/harmony/harmonyparser.go) | official source | One call at end of message; `index` left at 0. |
| [`openai/openai.go` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/openai/openai.go) | official source | OpenAI differences: arguments string, top-level index, `type`, `name` mapped to `tool_name`, `finish_reason` `tool_calls`. |
| [`docs/api/openai-compatibility.mdx` at `e9fde36`](https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api/openai-compatibility.mdx) | official docs | `tools` supported, `tool_choice` not. |
| In-repo renderers `qwen3coder.go`, `functiongemma.go`, `gemma4.go`, `glimmer.go`, `cohere.go` at `e9fde36` | official source | Which of `tool_name` and `tool_call_id` each renderer reads. |
| PR [#12956](https://github.com/ollama/ollama/pull/12956) merge `809b9c68` (5 November 2025) | official source | Introduced `ToolCall.ID` and `Message.ToolCallID`, and `toolCallId()`. |
| Tag [`v0.12.0`](https://github.com/ollama/ollama/blob/v0.12.0/api/types.go) vs [`v0.13.0`](https://github.com/ollama/ollama/blob/v0.13.0/api/types.go) (`604e43b28d12677c96675ba368eee20a2bed2c24`, 19 November 2025) | official source | `index` tag changed from `index,omitempty` to `index`. |
| [ollama.com/blog/tool-support](https://ollama.com/blog/tool-support) (25 July 2024) | official blog | Original tools object and `tool_calls` / `role: tool`. |
| [ollama.com/blog/functions-as-tools](https://ollama.com/blog/functions-as-tools) (25 November 2024) | official blog | `arguments` used as an object (`**tool.function.arguments`); loop over `tool_calls`. Python library, not the HTTP schema. |
| [ollama.com/blog/streaming-tool](https://ollama.com/blog/streaming-tool) (28 May 2025) | official blog | Multiple tools can be returned; streaming parser. This note’s question is the non-streaming body. |
| [ollama.com/blog/web-search](https://ollama.com/blog/web-search) (24 September 2025) | official blog | Follow-up message uses `role`, `content`, and `tool_name`. |
| Open PR [#17519](https://github.com/ollama/ollama/pull/17519) | official, **not merged** | Acknowledges the OpenAPI gap for `id`, `index`, `tool_name`, and `tool_call_id`. The gap was re-checked in `docs/openapi.yaml` at `e9fde36` and on the live chat page. The PR body is not the spec. |

Release tag [`v0.40.14`](https://github.com/ollama/ollama/releases/tag/v0.40.14) is the version label for this shape. `main` at `e9fde36` matches it for these files.

## Open questions

- A live `ollama serve` at this commit was not called, so the exact bytes of `created_at` and the random `id` were not captured. The pattern is the code cited above.
- Whether `"arguments"` sent **to** `/api/chat` as a JSON string is rejected was not executed. `ToolCallFunctionArguments.UnmarshalJSON` decodes into an ordered map, which is a JSON object. The model-output parser’s string handling is separate and runs before the response is built.
- Chat templates shipped inside GGUF files, outside this repo, were not read. In-repo renderers already disagree on `tool_name` versus `tool_call_id` versus order. For an arbitrary model, which field the prompt uses is unknown until that model’s template or renderer is read.
- `Tool.Items` (`json:"items,omitempty"` on the tool object, not on a property) is not in the docs. No in-repo renderer reading that tool-level field was found. What it does is unknown.
- Open PR #17519 was still open on 4 November 2026. When the published examples and OpenAPI will grow `id`, `index`, `tool_name`, and `tool_call_id` is unknown. Until then the Go structs are the wire format and the examples are a subset.
- Which models emit more than one call in one non-streaming response was not measured. The array allows it; the harmony parser does not.
