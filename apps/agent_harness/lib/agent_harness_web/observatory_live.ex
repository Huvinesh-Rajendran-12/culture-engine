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
  @lifecycle_events [:agent_started, :agent_stopped, :drone_completed, :drone_crashed]

  @impl true
  def handle_info({_agent_id, {event, _info}}, socket) when event in @lifecycle_events do
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

  defp icon_for_depth(0), do: "◈"
  defp icon_for_depth(1), do: "◆"
  defp icon_for_depth(_), do: "◇"

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

  defp selected_agent_name(agents, selected_id) do
    case Enum.find(agents, fn {a, _d} -> a.id == selected_id end) do
      {agent, _depth} -> agent.name
      nil -> selected_id
    end
  end

  @impl true
  def render(assigns) do
    ~H"""
    <nav class="nav">
      <a href="/" class="nav-brand">Culture Engine</a>
      <a href="/" class="nav-link">REPL</a>
      <a href="/observatory" class="nav-link active">Observatory</a>
      <div class="nav-spacer"></div>
      <div class="nav-status">
        <span style="color: var(--text-muted); font-size: 12px;">
          {length(@agents)} agent{if length(@agents) != 1, do: "s"}
        </span>
      </div>
    </nav>

    <div class="obs-layout">
      <div class="obs-sidebar">
        <div class="obs-title">Agents</div>

        <%= if @agents == [] do %>
          <p style="color: var(--text-muted); font-size: 13px; padding: 8px 0;">
            No agents running.
          </p>
        <% else %>
          <%= for {agent, depth} <- @agents do %>
            <div
              phx-click="select_agent"
              phx-value-id={agent.id}
              class={"obs-agent #{if @selected_id == agent.id, do: "selected"}"}
              style={"margin-left: #{depth * 20}px"}
            >
              <div class="obs-agent-name">
                <span style={"color: #{if depth == 0, do: "var(--accent-blue)", else: "var(--accent-purple)"}; font-size: 11px;"}>
                  {icon_for_depth(depth)}
                </span>
                {agent.name}
                <span class={"obs-tier #{agent.tier}"}>{agent.tier}</span>
              </div>
              <div class="obs-agent-meta">{agent.id}</div>
            </div>
          <% end %>
        <% end %>
      </div>

      <div class="obs-main">
        <%= if @selected_id do %>
          <div class="obs-title" style="display: flex; align-items: center; gap: 10px;">
            <span>{selected_agent_name(@agents, @selected_id)}</span>
            <span style="color: var(--text-muted); font-weight: 400; font-size: 11px; font-family: monospace;">{@selected_id}</span>
          </div>
          <div id="obs-events" phx-hook="ScrollBottom" style="max-height: calc(100vh - 110px); overflow-y: auto;">
            <%= for {evt, i} <- @events |> Enum.reverse() |> Enum.with_index() do %>
              <div id={"evt-#{i}"} class={"obs-event #{evt.type}"}>
                {evt.content}
              </div>
            <% end %>
          </div>
        <% else %>
          <div class="obs-empty">
            Select an agent to observe its event stream.
          </div>
        <% end %>
      </div>
    </div>
    """
  end
end
