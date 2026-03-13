defmodule AgentHarnessWeb.EventFormatter do
  @moduledoc "Converts agent events to `%{type, content}` display maps."

  def format({:text, text}), do: %{type: :text, content: text}

  def format({:tool_use, name, input}),
    do: %{type: :tool_use, content: "#{name}: #{inspect(input, pretty: true, limit: 5)}"}

  def format({:tool_result, name, result}),
    do: %{type: :tool_result, content: "#{name}: #{String.slice(result, 0..300)}"}

  def format({:error, reason}), do: %{type: :error, content: to_string(reason)}
  def format(:done), do: %{type: :system, content: "[done]"}
  def format(other), do: %{type: :system, content: inspect(other)}
end
