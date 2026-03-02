defmodule AgentHarness.Tools.CreateToolTest do
  use ExUnit.Case, async: false

  alias AgentHarness.Tools.CreateTool
  alias AgentHarness.ToolRegistry

  setup do
    for name <- ToolRegistry.tool_names(),
        name not in ~w(read_file list_files edit_file run_command search_files create_tool) do
      ToolRegistry.unregister(name)
    end

    :ok
  end

  test "creates a working tool via execute" do
    input = %{
      "name" => "greet",
      "description" => "Says hello",
      "input_schema" => %{
        "type" => "object",
        "properties" => %{
          "name" => %{"type" => "string", "description" => "Who to greet"}
        },
        "required" => ["name"]
      },
      "script" => "#!/bin/sh\necho \"hello\""
    }

    assert {:ok, msg} = CreateTool.execute(input)
    assert String.contains?(msg, "greet")
    assert String.contains?(msg, "created successfully")

    # Verify it's usable
    assert {:ok, "hello\n"} = ToolRegistry.execute("greet", %{"name" => "world"})
  end

  test "rejects name with spaces" do
    input = %{
      "name" => "bad name",
      "description" => "test",
      "input_schema" => %{"type" => "object", "properties" => %{}},
      "script" => "#!/bin/sh\necho ok"
    }

    assert {:error, msg} = CreateTool.execute(input)
    assert String.contains?(msg, "Invalid tool name")
  end

  test "rejects script without shebang" do
    input = %{
      "name" => "no_shebang",
      "description" => "test",
      "input_schema" => %{"type" => "object", "properties" => %{}},
      "script" => "echo ok"
    }

    assert {:error, msg} = CreateTool.execute(input)
    assert String.contains?(msg, "shebang")
  end

  test "rejects schema without type field" do
    input = %{
      "name" => "bad_schema",
      "description" => "test",
      "input_schema" => %{"properties" => %{}},
      "script" => "#!/bin/sh\necho ok"
    }

    assert {:error, msg} = CreateTool.execute(input)
    assert String.contains?(msg, "type")
  end

  test "rejects missing fields" do
    assert {:error, _} = CreateTool.execute(%{"name" => "partial"})
  end
end
