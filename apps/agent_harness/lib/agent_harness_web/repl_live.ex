defmodule AgentHarnessWeb.ReplLive do
  use Phoenix.LiveView

  @system_prompt "You are a helpful coding assistant with access to file tools. Use them to help the user."

  @impl true
  def mount(_params, _session, socket) do
    {:ok, agent} = AgentHarness.Agent.start_supervised(system: @system_prompt)
    _ref = Process.monitor(agent)
    identity = AgentHarness.Agent.get_identity(agent)

    {:ok,
     assign(socket,
       agent: agent,
       agent_name: identity.name,
       messages: [],
       loading: false,
       input: ""
     )}
  end

  @impl true
  def handle_event("submit", %{"input" => input}, socket) do
    input = String.trim(input)

    cond do
      input == "" ->
        {:noreply, socket}

      input == "/reset" ->
        AgentHarness.Agent.reset(socket.assigns.agent)

        {:noreply,
         assign(socket,
           messages: [%{role: :system, content: "[conversation reset]"}],
           input: ""
         )}

      true ->
        AgentHarness.Agent.chat_async(socket.assigns.agent, input)

        {:noreply,
         socket
         |> assign(loading: true, input: "")
         |> append_message(:user, input)}
    end
  end

  @impl true
  def handle_info({:agent_event, _agent_id, {:text, text}}, socket) do
    {:noreply, append_message(socket, :agent, text)}
  end

  def handle_info({:agent_event, _agent_id, {:tool_use, name, input}}, socket) do
    content = "#{name}: #{inspect(input, pretty: true, limit: 5)}"
    {:noreply, append_message(socket, :tool_use, content)}
  end

  def handle_info({:agent_event, _agent_id, {:tool_result, name, result}}, socket) do
    truncated = String.slice(result, 0..500)
    content = "#{name}: #{truncated}"
    {:noreply, append_message(socket, :tool_result, content)}
  end

  def handle_info({:agent_event, _agent_id, {:error, reason}}, socket) do
    {:noreply,
     socket
     |> assign(loading: false)
     |> append_message(:error, to_string(reason))}
  end

  def handle_info({:agent_event, _agent_id, :done}, socket) do
    {:noreply, assign(socket, loading: false)}
  end

  def handle_info({:DOWN, _ref, :process, _pid, _reason}, socket) do
    {:noreply,
     socket
     |> assign(loading: false)
     |> append_message(:system, "[agent process terminated]")}
  end

  defp append_message(socket, role, content) do
    message = %{role: role, content: content}
    assign(socket, messages: socket.assigns.messages ++ [message])
  end

  @impl true
  def render(assigns) do
    ~H"""
    <div id="repl-container">
      <div class="header">
        <span>{@agent_name}</span>
        <span class="tier-badge">mind</span>
      </div>

      <div class="messages" id="messages" phx-hook="ScrollBottom" phx-update="stream">
        <%= for {msg, i} <- Enum.with_index(@messages) do %>
          <div class={"message #{msg.role}"} id={"msg-#{i}"}><%= msg.content %></div>
        <% end %>

        <%= if @loading do %>
          <div class="loading-indicator" id="loading">thinking...</div>
        <% end %>
      </div>

      <div class="input-area">
        <form phx-submit="submit">
          <input
            type="text"
            name="input"
            value={@input}
            placeholder={if @loading, do: "Agent is thinking...", else: "Type a message... (/reset to clear)"}
            disabled={@loading}
            autofocus
          />
          <button type="submit" disabled={@loading}>Send</button>
        </form>
      </div>
    </div>
    """
  end
end
