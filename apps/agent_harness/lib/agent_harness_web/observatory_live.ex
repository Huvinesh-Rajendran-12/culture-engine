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

  @max_events 500

  # Agent events from "agent:<id>" topic
  def handle_info({:agent_event, _agent_id, event}, socket) do
    entry = EventFormatter.format(event)
    events = [entry | socket.assigns.events] |> Enum.take(@max_events)
    {:noreply, assign(socket, events: events)}
  end

  def handle_info(_msg, socket), do: {:noreply, socket}

  defp load_agents do
    raw = AgentHarness.Agent.list_agents()
    pid_to_id = Map.new(raw, fn {id, pid, _meta} -> {pid, id} end)

    agents =
      Enum.map(raw, fn {id, _pid, meta} ->
        %{
          id: id,
          name: meta[:name] || "unknown",
          tier: meta[:tier] || :unknown,
          parent: meta[:parent],
          parent_id: if(meta[:parent], do: Map.get(pid_to_id, meta[:parent]))
        }
      end)

    minds = agents |> Enum.filter(&(&1.tier == :mind)) |> Enum.sort_by(& &1.name)
    drones = Enum.filter(agents, &(&1.tier == :drone))

    # Build tree: each mind followed by its drones
    Enum.flat_map(minds, fn mind ->
      children = drones |> Enum.filter(&(&1.parent_id == mind.id)) |> Enum.sort_by(& &1.name)
      [mind | children]
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
          <%= for agent <- @agents do %>
            <div
              phx-click="select_agent"
              phx-value-id={agent.id}
              style={"padding: 10px 12px; margin-bottom: 6px; border-radius: 6px; cursor: pointer; margin-left: #{if agent.tier == :drone, do: "24px", else: "0"}; border: 1px solid #{if @selected_id == agent.id, do: "#58a6ff", else: "#21262d"}; background: #{if @selected_id == agent.id, do: "#161b22", else: "transparent"}; border-left: 3px solid #{if agent.tier == :drone, do: "#8b5cf6", else: if(@selected_id == agent.id, do: "#58a6ff", else: "#21262d")};"}
            >
              <div style="font-size: 13px; font-weight: 600; color: #c9d1d9; display: flex; align-items: center; gap: 6px;">
                <span style={"color: #{if agent.tier == :drone, do: "#d2a8ff", else: "#58a6ff"}; font-size: 10px;"}>{if agent.tier == :drone, do: "◆", else: "◈"}</span>
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
