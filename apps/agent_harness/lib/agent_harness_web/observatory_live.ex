defmodule AgentHarnessWeb.ObservatoryLive do
  @moduledoc """
  LiveView for observing all running agents — the Culture Observatory.

  Left panel: tree of agents (Mind -> Drone hierarchy).
  Right panel: selected agent's conversation stream.
  """
  use Phoenix.LiveView

  alias AgentHarnessWeb.EventFormatter

  @impl true
  def mount(_params, _session, socket) do
    if connected?(socket) do
      Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agents")
    end

    agents = load_agents()

    {:ok,
     assign(socket,
       agents: agents,
       selected_id: nil,
       events: []
     )}
  end

  @impl true
  def handle_event("select_agent", %{"id" => id}, socket) do
    # Unsubscribe from previous agent's topic
    if socket.assigns.selected_id do
      Phoenix.PubSub.unsubscribe(AgentHarness.PubSub, "agent:#{socket.assigns.selected_id}")
    end

    # Subscribe to new agent's topic
    Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agent:#{id}")

    {:noreply, assign(socket, selected_id: id, events: [])}
  end

  # Lifecycle events from "agents" topic
  @impl true
  def handle_info({_agent_id, {:agent_started, _info}}, socket) do
    {:noreply, assign(socket, agents: load_agents())}
  end

  def handle_info({_agent_id, {:agent_stopped, _info}}, socket) do
    {:noreply, assign(socket, agents: load_agents())}
  end

  def handle_info({_agent_id, {:drone_completed, _info}}, socket) do
    {:noreply, assign(socket, agents: load_agents())}
  end

  def handle_info({_agent_id, {:drone_crashed, _info}}, socket) do
    {:noreply, assign(socket, agents: load_agents())}
  end

  @max_events 500

  # Agent events from "agent:<id>" topic
  def handle_info({:agent_event, _agent_id, event}, socket) do
    entry = EventFormatter.format(event)
    events = [entry | socket.assigns.events] |> Enum.take(@max_events)
    {:noreply, assign(socket, events: events)}
  end

  def handle_info(_msg, socket), do: {:noreply, socket}

  defp agent_card_style(agent, depth, selected_id) do
    selected = selected_id == agent.id

    border_color = if selected, do: "#58a6ff", else: "#21262d"

    left_border_color =
      cond do
        depth == 0 and selected -> "#58a6ff"
        depth == 0 -> "#21262d"
        depth == 1 -> "#8b5cf6"
        true -> "#6b46a8"
      end

    [
      "padding: 10px 12px",
      "margin-bottom: 6px",
      "border-radius: 6px",
      "cursor: pointer",
      "margin-left: #{depth * 24}px",
      "border: 1px solid #{border_color}",
      "background: #{if selected, do: "#161b22", else: "transparent"}",
      "border-left: 3px solid #{left_border_color}"
    ]
    |> Enum.join("; ")
  end

  defp icon_for_depth(0), do: "◈"
  defp icon_for_depth(1), do: "◆"
  defp icon_for_depth(_), do: "◇"

  defp icon_color(0), do: "#58a6ff"
  defp icon_color(1), do: "#d2a8ff"
  defp icon_color(_), do: "#a78bfa"

  defp load_agents do
    raw = AgentHarness.Agent.list_agents()
    pid_to_id = Map.new(raw, fn {id, pid, _meta} -> {pid, id} end)

    agents =
      Enum.map(raw, fn {id, _pid, meta} ->
        %{
          id: id,
          name: meta[:name] || "unknown",
          tier: meta[:tier] || :unknown,
          parent_id: if(meta[:parent], do: Map.get(pid_to_id, meta[:parent]))
        }
      end)

    # Group by parent_id — nil means root (mind)
    children_map = Enum.group_by(agents, & &1.parent_id)
    roots = Map.get(children_map, nil, []) |> Enum.sort_by(& &1.name)

    flatten_tree(roots, children_map, 0)
  end

  defp flatten_tree(nodes, children_map, depth) do
    Enum.flat_map(nodes, fn agent ->
      children = Map.get(children_map, agent.id, []) |> Enum.sort_by(& &1.name)
      [{agent, depth} | flatten_tree(children, children_map, depth + 1)]
    end)
  end

  @impl true
  def render(assigns) do
    ~H"""
    <div id="observatory" style="display: flex; height: 100vh; font-family: 'SF Mono', monospace; background: #0d1117; color: #c9d1d9;">
      <div style="width: 320px; border-right: 1px solid #21262d; padding: 16px; overflow-y: auto;">
        <h2 style="color: #58a6ff; font-size: 16px; margin-bottom: 16px;">Observatory</h2>

        <%= if @agents == [] do %>
          <p style="color: #8b949e; font-size: 13px;">No agents running.</p>
        <% else %>
          <%= for {agent, depth} <- @agents do %>
            <div
              phx-click="select_agent"
              phx-value-id={agent.id}
              style={agent_card_style(agent, depth, @selected_id)}
            >
              <div style="font-size: 13px; font-weight: 600; color: #c9d1d9; display: flex; align-items: center; gap: 6px;">
                <span style={"color: #{icon_color(depth)}; font-size: 10px;"}>{icon_for_depth(depth)}</span>
                {agent.name}
              </div>
              <div style="font-size: 11px; color: #8b949e; margin-top: 2px;">
                <span class={"tier-badge #{agent.tier}"}>{agent.tier}</span>
                <span style="margin-left: 8px;">{agent.id}</span>
              </div>
            </div>
          <% end %>
        <% end %>
      </div>

      <div style="flex: 1; padding: 16px; overflow-y: auto;">
        <%= if @selected_id do %>
          <h3 style="color: #58a6ff; font-size: 14px; margin-bottom: 12px;">
            Events for {@selected_id}
          </h3>
          <div id="obs-events" phx-hook="ScrollBottom" style="max-height: calc(100vh - 80px); overflow-y: auto;">
            <%= for {evt, i} <- @events |> Enum.reverse() |> Enum.with_index() do %>
              <div id={"evt-#{i}"} class={"message #{evt.type}"} style="margin-bottom: 8px; padding: 6px 10px; border-radius: 4px; font-size: 13px; white-space: pre-wrap;">
                {evt.content}
              </div>
            <% end %>
          </div>
        <% else %>
          <p style="color: #8b949e; font-size: 14px; margin-top: 40px; text-align: center;">
            Select an agent to observe its event stream.
          </p>
        <% end %>
      </div>
    </div>
    """
  end
end
