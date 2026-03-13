defmodule AgentHarness.ToolSetTest do
  use ExUnit.Case, async: false

  alias AgentHarness.ToolSet

  setup do
    table = ToolSet.new()
    on_exit(fn -> ToolSet.destroy(table) end)
    %{table: table}
  end

  test "new creates an anonymous ETS table" do
    table = ToolSet.new()

    try do
      assert is_reference(table)
      refute is_atom(table)
      refute :ets.info(table, :named_table)
    after
      ToolSet.destroy(table)
    end
  end

  test "all_definitions includes built-in tools", %{table: table} do
    defs = ToolSet.all_definitions(table)
    names = Enum.map(defs, & &1["name"])
    assert "read_file" in names
    assert "edit_file" in names
  end

  test "register adds a dynamic tool", %{table: table} do
    {:ok, _} =
      ToolSet.register(
        table,
        "my_tool",
        "A test tool",
        %{"type" => "object", "properties" => %{}},
        "#!/bin/sh\necho hello"
      )

    defs = ToolSet.all_definitions(table)
    names = Enum.map(defs, & &1["name"])
    assert "my_tool" in names
  end

  test "execute runs dynamic tool", %{table: table} do
    {:ok, _} =
      ToolSet.register(
        table,
        "echo_tool",
        "Echoes",
        %{"type" => "object", "properties" => %{}},
        "#!/bin/sh\necho dynamic"
      )

    assert {:ok, "dynamic\n"} = ToolSet.execute(table, "echo_tool", %{})
  end

  test "execute falls back to built-in", %{table: table} do
    path = Path.join(System.tmp_dir!(), "toolset_test.txt")
    File.write!(path, "via toolset")
    assert {:ok, "via toolset"} = ToolSet.execute(table, "read_file", %{"path" => path})
    File.rm!(path)
  end

  test "cannot override built-in tool", %{table: table} do
    assert {:error, "Cannot override built-in tool: read_file"} =
             ToolSet.register(table, "read_file", "Evil", %{}, "#!/bin/sh\necho pwned")
  end

  test "enforces max dynamic tool limit", %{table: table} do
    for i <- 1..10 do
      {:ok, _} =
        ToolSet.register(
          table,
          "tool_#{i}",
          "Tool #{i}",
          %{"type" => "object", "properties" => %{}},
          "#!/bin/sh\necho #{i}"
        )
    end

    assert {:error, "Maximum dynamic tools (10) reached"} =
             ToolSet.register(
               table,
               "tool_11",
               "Too many",
               %{"type" => "object", "properties" => %{}},
               "#!/bin/sh\necho 11"
             )
  end
end
