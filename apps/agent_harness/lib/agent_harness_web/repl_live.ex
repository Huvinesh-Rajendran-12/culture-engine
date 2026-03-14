defmodule AgentHarnessWeb.ReplLive do
  use Phoenix.LiveView

  alias AgentHarnessWeb.EventFormatter

  @max_drone_events 200

  @impl true
  def mount(_params, _session, socket) do
    {:ok, agent} =
      AgentHarness.Agent.start_supervised(system: AgentHarness.Prompts.default(:mind))

    _ref = Process.monitor(agent)
    identity = AgentHarness.Agent.get_identity(agent)

    if connected?(socket) do
      Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agents")
    end

    {:ok,
     assign(socket,
       agent: agent,
       agent_name: identity.name,
       messages: [],
       loading: false,
       input: "",
       drones: %{},
       pending_spawn: nil,
       active_drone_count: 0
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
           messages: [%{role: :system, content: "Conversation reset."}],
           input: "",
           drones: %{},
           pending_spawn: nil,
           active_drone_count: 0
         )}

      true ->
        AgentHarness.Agent.chat_async(socket.assigns.agent, input)

        {:noreply,
         socket
         |> assign(loading: true, input: "")
         |> append_message(:user, input)}
    end
  end

  def handle_event("toggle_drone", %{"id" => drone_id}, socket) do
    {:noreply, update_drone(socket, drone_id, &%{&1 | collapsed: !&1.collapsed})}
  end

  # --- Lifecycle events from "agents" global topic ---

  @impl true
  def handle_info({drone_id, {:agent_started, %{tier: :drone, parent: parent} = info}}, socket) do
    if parent == socket.assigns.agent and not is_map_key(socket.assigns.drones, drone_id) do
      Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agent:#{drone_id}")

      task = if socket.assigns.pending_spawn, do: socket.assigns.pending_spawn.task, else: ""

      drone = %{
        id: drone_id,
        name: info.name,
        task: task,
        status: :running,
        events: [],
        collapsed: false
      }

      new_drones = Map.put(socket.assigns.drones, drone_id, drone)

      {:noreply,
       socket
       |> assign(drones: new_drones, pending_spawn: nil, active_drone_count: active_drone_count(new_drones))
       |> append_message(:drone_spawn, drone_id)}
    else
      {:noreply, socket}
    end
  end

  def handle_info({drone_id, {:agent_stopped, _info}}, socket)
      when is_map_key(socket.assigns.drones, drone_id) do
    {:noreply, update_drone(socket, drone_id, &%{&1 | status: :complete, collapsed: true})}
  end

  def handle_info({drone_id, {:drone_crashed, info}}, socket)
      when is_map_key(socket.assigns.drones, drone_id) do
    evt = %{type: :error, content: "Crashed: #{info.reason}"}

    {:noreply,
     update_drone(socket, drone_id, &%{&1 | status: :error, events: cap_events(&1.events, evt)})}
  end

  # Ignore lifecycle events for other agents
  def handle_info({_id, {:agent_started, _}}, socket), do: {:noreply, socket}
  def handle_info({_id, {:agent_stopped, _}}, socket), do: {:noreply, socket}
  def handle_info({_id, {:drone_crashed, _}}, socket), do: {:noreply, socket}

  # --- Drone events from "agent:<drone_id>" PubSub topic ---

  def handle_info({:agent_event, drone_id, event}, socket)
      when is_map_key(socket.assigns.drones, drone_id) do
    case event do
      :done ->
        {:noreply, update_drone(socket, drone_id, &%{&1 | status: :complete, collapsed: true})}

      _ ->
        evt = EventFormatter.format(event)
        {:noreply, update_drone(socket, drone_id, &%{&1 | events: cap_events(&1.events, evt)})}
    end
  end

  # --- Mind agent events (from direct send) ---

  # Intercept spawn_agent tool_use — store pending spawn info
  def handle_info({:agent_event, _agent_id, {:tool_use, "spawn_agent", input}}, socket) do
    {:noreply, assign(socket, pending_spawn: %{task: input["task"] || "", name: input["name"]})}
  end

  # Suppress spawn_agent tool_result when a drone panel was created
  def handle_info({:agent_event, _agent_id, {:tool_result, "spawn_agent", result}}, socket) do
    if socket.assigns.pending_spawn != nil do
      {:noreply,
       socket
       |> assign(pending_spawn: nil)
       |> append_message(:error, "Drone spawn failed: #{inspect(result, limit: 100)}")}
    else
      {:noreply, socket}
    end
  end

  def handle_info({:agent_event, _agent_id, {:text, text}}, socket) do
    {:noreply, append_message(socket, :agent, text)}
  end

  def handle_info({:agent_event, _agent_id, {:tool_use, name, input}}, socket) do
    %{content: content} = EventFormatter.format({:tool_use, name, input})
    {:noreply, append_message(socket, :tool_use, %{name: name, detail: content})}
  end

  def handle_info({:agent_event, _agent_id, {:tool_result, name, result}}, socket) do
    %{content: content} = EventFormatter.format({:tool_result, name, result})
    {:noreply, attach_tool_result(socket, name, content)}
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
     |> append_message(:system, "Agent process terminated.")}
  end

  def handle_info(_msg, socket), do: {:noreply, socket}

  # Attach a tool result to the most recent tool_use message with matching name
  defp attach_tool_result(socket, name, result_content) do
    messages =
      socket.assigns.messages
      |> Enum.reverse()
      |> attach_result_to_first(name, result_content)
      |> Enum.reverse()

    assign(socket, messages: messages)
  end

  defp attach_result_to_first([], _name, _result), do: []

  defp attach_result_to_first([%{role: :tool_use, content: %{name: n} = content} = msg | rest], name, result)
       when n == name and not is_map_key(content, :result) do
    [%{msg | content: Map.put(content, :result, result)} | rest]
  end

  defp attach_result_to_first([h | t], name, result) do
    [h | attach_result_to_first(t, name, result)]
  end

  defp append_message(socket, role, content) do
    message = %{role: role, content: content}
    assign(socket, messages: socket.assigns.messages ++ [message])
  end

  defp update_drone(socket, drone_id, fun) do
    case Map.get(socket.assigns.drones, drone_id) do
      nil ->
        socket

      drone ->
        new_drones = Map.put(socket.assigns.drones, drone_id, fun.(drone))
        assign(socket, drones: new_drones, active_drone_count: active_drone_count(new_drones))
    end
  end

  defp cap_events(events, new_event) do
    [new_event | events] |> Enum.take(@max_drone_events)
  end

  defp active_drone_count(drones) do
    Enum.count(drones, fn {_id, d} -> d.status == :running end)
  end

  defp drone_status_text(:running), do: "running"
  defp drone_status_text(:complete), do: "done"
  defp drone_status_text(:error), do: "error"
  defp drone_status_text(_), do: ""

  @impl true
  def render(assigns) do
    ~H"""
    <AgentHarnessWeb.Layouts.nav page={:repl}>
      <:status>
        <div class="dot"></div>
        <span class="mono">{@agent_name}</span>
        <span class="tier-badge mind">mind</span>
        <%= if @active_drone_count > 0 do %>
          <span style="margin-left: 4px; color: var(--accent-purple);">
            +{@active_drone_count} drone{if @active_drone_count != 1, do: "s"}
          </span>
        <% end %>
      </:status>
    </AgentHarnessWeb.Layouts.nav>

    <div class="app-shell">
      <div class="conversation" id="messages" phx-hook="ScrollBottom">
        <div class="conversation-inner">
          <%= for {msg, i} <- Enum.with_index(@messages) do %>
            <%= case msg.role do %>
              <% :user -> %>
                <div class="msg msg-user" id={"msg-#{i}"}>
                  <div class="msg-label">You</div>
                  {msg.content}
                </div>

              <% :agent -> %>
                <div class="msg msg-agent" id={"msg-#{i}"}>
                  {msg.content}
                </div>

              <% :tool_use -> %>
                <div class="msg tool-group" id={"msg-#{i}"}>
                  <div class="tool-header" phx-hook="ToolToggle" id={"tool-toggle-#{i}"}>
                    <span class="tool-icon">&#9654;</span>
                    <span class="tool-name">{msg.content.name}</span>
                    <span style="color: var(--text-muted); font-size: 11px;">click to expand</span>
                  </div>
                  <div class="tool-body">
                    <div class="tool-input">{msg.content.detail}</div>
                    <%= if Map.has_key?(msg.content, :result) do %>
                      <div class="tool-result">{msg.content.result}</div>
                    <% end %>
                  </div>
                </div>

              <% :error -> %>
                <div class="msg msg-error" id={"msg-#{i}"}>{msg.content}</div>

              <% :system -> %>
                <div class="msg msg-system" id={"msg-#{i}"}>{msg.content}</div>

              <% :drone_spawn -> %>
                <% drone = @drones[msg.content] %>
                <%= if drone do %>
                  <div class={"msg drone-panel #{drone.status}"} id={"msg-#{i}"}>
                    <div class="drone-header" phx-click="toggle_drone" phx-value-id={drone.id}>
                      <span class="drone-icon">&#9670;</span>
                      <div class="drone-info">
                        <div class="drone-name">
                          {drone.name}
                          <span class="tier-badge drone" style="margin-left: 8px;">drone</span>
                        </div>
                        <%= if drone.task != "" do %>
                          <div class="drone-task-text">{drone.task}</div>
                        <% end %>
                      </div>
                      <span class={"drone-badge #{drone.status}"}>{drone_status_text(drone.status)}</span>
                      <span class={"drone-toggle #{unless drone.collapsed, do: "open"}"}>&#9654;</span>
                    </div>
                    <%= unless drone.collapsed do %>
                      <div class="drone-events">
                        <%= for {evt, j} <- Enum.with_index(Enum.reverse(drone.events)) do %>
                          <div class={"drone-event #{evt.type}"} id={"drone-#{drone.id}-evt-#{j}"}>{evt.content}</div>
                        <% end %>
                        <%= if drone.status == :running do %>
                          <div class="thinking">
                            <span class="thinking-dots"><span></span><span></span><span></span></span>
                            drone working
                          </div>
                        <% end %>
                      </div>
                    <% end %>
                  </div>
                <% end %>

              <% _ -> %>
                <div class="msg msg-system" id={"msg-#{i}"}>{inspect(msg)}</div>
            <% end %>
          <% end %>

          <%= if @loading and @active_drone_count == 0 do %>
            <div class="thinking" id="loading">
              <span class="thinking-dots"><span></span><span></span><span></span></span>
              thinking
            </div>
          <% end %>
        </div>
      </div>

      <div class="input-area">
        <div class="input-inner">
          <form class="input-form" phx-submit="submit">
            <div class="input-wrap">
              <textarea
                name="input"
                class="input-field"
                phx-hook="AutoResize"
                id="chat-input"
                rows="1"
                placeholder={if @loading, do: "Mind is working...", else: "Message the Mind... (Shift+Enter for newline)"}
                disabled={@loading}
                autofocus
              >{@input}</textarea>
            </div>
            <button type="submit" class="send-btn" disabled={@loading}>Send</button>
          </form>
        </div>
      </div>
    </div>
    """
  end
end
