defmodule AgentHarnessWeb.ReplLive do
  use Phoenix.LiveView

  alias AgentHarnessWeb.EventFormatter

  @max_drone_events 200

  @impl true
  def mount(_params, _session, socket) do
    {:ok, agent} = AgentHarness.Agent.start_supervised(system: AgentHarness.Prompts.default(:mind))
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
       pending_spawn: nil
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
           input: "",
           drones: %{},
           pending_spawn: nil
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

      {:noreply,
       socket
       |> assign(drones: Map.put(socket.assigns.drones, drone_id, drone), pending_spawn: nil)
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
    {:noreply, update_drone(socket, drone_id, &%{&1 | status: :error, events: cap_events(&1.events, evt)})}
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

  # Intercept spawn_agent tool_use — store pending spawn info, don't render as regular message
  def handle_info({:agent_event, _agent_id, {:tool_use, "spawn_agent", input}}, socket) do
    {:noreply, assign(socket, pending_spawn: %{task: input["task"] || "", name: input["name"]})}
  end

  # Suppress spawn_agent tool_result when a drone panel was created — shown there instead.
  # If pending_spawn is still set, agent_started never fired (spawn failed), so surface the error.
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
    {:noreply, append_message(socket, :tool_use, content)}
  end

  def handle_info({:agent_event, _agent_id, {:tool_result, name, result}}, socket) do
    %{content: content} = EventFormatter.format({:tool_result, name, result})
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

  def handle_info(_msg, socket), do: {:noreply, socket}

  defp append_message(socket, role, content) do
    message = %{role: role, content: content}
    assign(socket, messages: socket.assigns.messages ++ [message])
  end

  defp update_drone(socket, drone_id, fun) do
    case Map.get(socket.assigns.drones, drone_id) do
      nil -> socket
      drone -> assign(socket, drones: Map.put(socket.assigns.drones, drone_id, fun.(drone)))
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
    assigns = assign(assigns, :active_drone_count, active_drone_count(assigns.drones))

    ~H"""
    <div id="repl-container">
      <div class="header">
        <span class="header-icon">◈</span>
        <span>{@agent_name}</span>
        <span class="tier-badge">mind</span>
        <%= if @active_drone_count > 0 do %>
          <span class="drone-count">
            {@active_drone_count} drone{if @active_drone_count != 1, do: "s"} active
          </span>
        <% end %>
      </div>

      <div class="messages" id="messages" phx-hook="ScrollBottom" phx-update="stream">
        <%= for {msg, i} <- Enum.with_index(@messages) do %>
          <%= if msg.role == :drone_spawn do %>
            <% drone = @drones[msg.content] %>
            <%= if drone do %>
              <div class={"drone-panel #{drone.status} #{if drone.collapsed, do: "collapsed", else: ""}"} id={"msg-#{i}"}>
                <div class="drone-header" phx-click="toggle_drone" phx-value-id={drone.id}>
                  <span class="drone-indicator">◆</span>
                  <span class="tier-badge drone">drone</span>
                  <span class="drone-name">{drone.name}</span>
                  <span class={"drone-status-badge #{drone.status}"}>{drone_status_text(drone.status)}</span>
                  <span class="drone-toggle">{if drone.collapsed, do: "▶", else: "▼"}</span>
                </div>
                <%= if drone.task != "" do %>
                  <div class="drone-task">{drone.task}</div>
                <% end %>
                <%= unless drone.collapsed do %>
                  <div class="drone-events">
                    <%= for {evt, j} <- Enum.with_index(Enum.reverse(drone.events)) do %>
                      <div class={"drone-event #{evt.type}"} id={"drone-#{drone.id}-evt-#{j}"}>{evt.content}</div>
                    <% end %>
                    <%= if drone.status == :running do %>
                      <div class="loading-indicator">thinking...</div>
                    <% end %>
                  </div>
                <% end %>
              </div>
            <% end %>
          <% else %>
            <div class={"message #{msg.role}"} id={"msg-#{i}"}><%= msg.content %></div>
          <% end %>
        <% end %>

        <%= if @loading and @active_drone_count == 0 do %>
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
