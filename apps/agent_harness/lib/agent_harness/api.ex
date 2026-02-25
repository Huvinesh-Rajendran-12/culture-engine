defmodule AgentHarness.API do
  @moduledoc """
  Thin HTTP client for the Anthropic Messages API.
  Supports both direct Anthropic and OpenRouter as a proxy.

  Set OPENROUTER_API_KEY to use OpenRouter, or ANTHROPIC_API_KEY for direct access.
  OpenRouter takes priority if both are set.
  """

  @anthropic_url "https://api.anthropic.com/v1/messages"
  @openrouter_url "https://openrouter.ai/api/v1/messages"
  @api_version "2023-06-01"

  def chat(messages, tools, opts \\ []) do
    {api_key, api_url} = resolve_provider(opts)
    model = opts[:model] || "claude-sonnet-4-20250514"
    system = opts[:system]
    max_tokens = opts[:max_tokens] || 8096

    body =
      %{
        "model" => model,
        "max_tokens" => max_tokens,
        "messages" => messages,
        "tools" => tools
      }
      |> maybe_put("system", system)

    case Req.post(api_url,
           json: body,
           headers: [
             {"x-api-key", api_key},
             {"anthropic-version", @api_version},
             {"content-type", "application/json"}
           ],
           receive_timeout: 120_000
         ) do
      {:ok, %Req.Response{status: 200, body: body}} ->
        {:ok, body}

      {:ok, %Req.Response{status: status, body: body}} ->
        {:error, "API returned #{status}: #{inspect(body)}"}

      {:error, reason} ->
        {:error, "Request failed: #{inspect(reason)}"}
    end
  end

  defp resolve_provider(opts) do
    cond do
      key = opts[:api_key] ->
        url = opts[:api_url] || @anthropic_url
        {key, url}

      key = System.get_env("OPENROUTER_API_KEY") ->
        {key, @openrouter_url}

      key = System.get_env("ANTHROPIC_API_KEY") ->
        {key, @anthropic_url}

      true ->
        raise "No API key set. Export OPENROUTER_API_KEY or ANTHROPIC_API_KEY."
    end
  end

  defp maybe_put(map, _key, nil), do: map
  defp maybe_put(map, key, value), do: Map.put(map, key, value)
end
