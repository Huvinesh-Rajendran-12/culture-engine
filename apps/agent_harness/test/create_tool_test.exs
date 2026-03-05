defmodule AgentHarness.Tools.CreateToolTest do
  use ExUnit.Case, async: false

  alias AgentHarness.Tools.CreateTool
  alias AgentHarness.ToolRegistry

  setup do
    for name <- ToolRegistry.tool_names(),
        name not in ToolRegistry.builtin_names() do
      ToolRegistry.unregister(name)
    end

    :ok
  end

  test "validate accepts valid input" do
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

    assert :ok = CreateTool.validate(input)
  end

  test "rejects name with spaces" do
    input = %{
      "name" => "bad name",
      "description" => "test",
      "input_schema" => %{"type" => "object", "properties" => %{}},
      "script" => "#!/bin/sh\necho ok"
    }

    assert {:error, msg} = CreateTool.validate(input)
    assert String.contains?(msg, "Invalid tool name")
  end

  test "rejects script without shebang" do
    input = %{
      "name" => "no_shebang",
      "description" => "test",
      "input_schema" => %{"type" => "object", "properties" => %{}},
      "script" => "echo ok"
    }

    assert {:error, msg} = CreateTool.validate(input)
    assert String.contains?(msg, "shebang")
  end

  test "rejects schema without type field" do
    input = %{
      "name" => "bad_schema",
      "description" => "test",
      "input_schema" => %{"properties" => %{}},
      "script" => "#!/bin/sh\necho ok"
    }

    assert {:error, msg} = CreateTool.validate(input)
    assert String.contains?(msg, "type")
  end

  test "rejects missing fields" do
    assert {:error, _} = CreateTool.validate(%{"name" => "partial"})
  end
end
