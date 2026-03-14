defmodule AgentHarnessWeb.ObservatoryLive do
  @moduledoc """
  LiveView for observing all running agents — the Culture Observatory.

  Left panel: tree of agents (Mind -> Drone hierarchy).
  Right panel: selected agent's conversation stream.
  """
  use Phoenix.LiveView

  alias AgentHarnessWeb.EventFormatter

  @max_events 500

  @impl true
  def mount(_params, _session, socket) do
    if connected?(socket) do
      Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agents")
    end

    agents = load_agents()

    {:ok,
     assign(socket,
       agents: agents,
       agent_count: length(agents),
       selected_id: nil,
       selected_name: nil,
       events: []
     )}
  end

  @impl true
  def handle_event("select_agent", %{"id" => id}, socket) do
    if socket.assigns.selected_id do
      Phoenix.PubSub.unsubscribe(AgentHarness.PubSub, "agent:#{socket.assigns.selected_id}")
    end

    Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agent:#{id}")

    name =
      case Enum.find(socket.assigns.agents, fn {a, _d} -> a.id == id end) do
        {agent, _depth} -> agent.name
        nil -> id
      end

    history = load_event_history(id)

    {:noreply, assign(socket, selected_id: id, selected_name: name, events: history)}
  end

  # Lifecycle events from "agents" topic
  @lifecycle_events [:agent_started, :agent_stopped, :drone_completed, :drone_crashed]

  @impl true
  def handle_info({_agent_id, {event, _info}}, socket) when event in @lifecycle_events do
    agents = load_agents()
    {:noreply, assign(socket, agents: agents, agent_count: length(agents))}
  end

  # Agent events from "agent:<id>" topic — prepend newest first
  def handle_info({:agent_event, _agent_id, event}, socket) do
    entry = EventFormatter.format(event)
    events = [entry | socket.assigns.events] |> Enum.take(@max_events)
    {:noreply, assign(socket, events: events)}
  end

  def handle_info(_msg, socket), do: {:noreply, socket}

  defp load_event_history(agent_id) do
    via = {:via, Registry, {AgentHarness.AgentRegistry, agent_id}}

    via
    |> AgentHarness.Agent.get_events()
    |> Enum.map(&EventFormatter.format/1)
  catch
    :exit, _ -> []
  end

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
    # Reverse events once for chronological display (stored newest-first)
    assigns = assign(assigns, :display_events, Enum.reverse(assigns.events))

    ~H"""
    <AgentHarnessWeb.Layouts.nav page={:observatory}>
      <:status>
        <span style="color: var(--text-muted); font-size: 12px;">
          {@agent_count} agent{if @agent_count != 1, do: "s"}
        </span>
      </:status>
    </AgentHarnessWeb.Layouts.nav>

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
                <span class={"obs-agent-icon #{if depth == 0, do: "mind", else: "drone"}"}>
                  {icon_for_depth(depth)}
                </span>
                {agent.name}
                <span class={"tier-badge #{agent.tier}"}>{agent.tier}</span>
              </div>
              <div class="obs-agent-meta">{agent.id}</div>
            </div>
          <% end %>
        <% end %>
      </div>

      <div class="obs-main">
        <%= if @selected_id do %>
          <div class="obs-title" style="display: flex; align-items: center; gap: 10px;">
            <span>{@selected_name}</span>
            <span style="color: var(--text-muted); font-weight: 400; font-size: 11px; font-family: monospace;">{@selected_id}</span>
          </div>
          <div id="obs-events" phx-hook="ScrollBottom" style="max-height: calc(100vh - 110px); overflow-y: auto;">
            <%= for {evt, i} <- Enum.with_index(@display_events) do %>
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
