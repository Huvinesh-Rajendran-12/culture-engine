defmodule AgentHarness.ToolRegistryTest do
  use ExUnit.Case, async: false

  alias AgentHarness.ToolRegistry

  setup do
    # Clean up any dynamic tools between tests
    for name <- ToolRegistry.tool_names(),
        name not in ~w(read_file list_files edit_file run_command search_files create_tool) do
      ToolRegistry.unregister(name)
    end

    :ok
  end

  describe "built-in tools" do
    test "all_definitions includes built-in tools" do
      defs = ToolRegistry.all_definitions()
      names = Enum.map(defs, & &1["name"])

      assert "read_file" in names
      assert "edit_file" in names
      assert "list_files" in names
      assert "run_command" in names
      assert "search_files" in names
      assert "create_tool" in names
    end

    test "execute dispatches to built-in tool module" do
      # read_file with a non-existent path should return an error
      assert {:error, "File not found: /nonexistent_file_abc123"} =
               ToolRegistry.execute("read_file", %{"path" => "/nonexistent_file_abc123"})
    end

    test "execute returns error for unknown tool" do
      assert {:error, "Unknown tool: no_such_tool"} =
               ToolRegistry.execute("no_such_tool", %{})
    end
  end

  describe "dynamic tool registration" do
    test "register and execute a script-based tool" do
      script = """
      #!/bin/sh
      echo "hello from dynamic tool"
      """

      assert {:ok, "my_tool"} =
               ToolRegistry.register(
                 "my_tool",
                 "A test tool",
                 %{"type" => "object", "properties" => %{}},
                 script
               )

      # Should appear in definitions
      names = ToolRegistry.all_definitions() |> Enum.map(& &1["name"])
      assert "my_tool" in names

      # Should be executable
      assert {:ok, "hello from dynamic tool\n"} =
               ToolRegistry.execute("my_tool", %{})
    end

    test "script receives input via TOOL_INPUT env var" do
      script = """
      #!/bin/sh
      echo "$TOOL_INPUT"
      """

      assert {:ok, "env_tool"} =
               ToolRegistry.register(
                 "env_tool",
                 "Echoes input back",
                 %{"type" => "object", "properties" => %{"msg" => %{"type" => "string"}}},
                 script
               )

      assert {:ok, output} = ToolRegistry.execute("env_tool", %{"msg" => "test"})
      assert String.contains?(output, "msg")
      assert String.contains?(output, "test")
    end

    test "cannot override built-in tool" do
      assert {:error, "Cannot override built-in tool: read_file"} =
               ToolRegistry.register("read_file", "Evil", %{}, "#!/bin/sh\necho pwned")
    end

    test "can unregister dynamic tool" do
      script = "#!/bin/sh\necho ok"

      {:ok, _} =
        ToolRegistry.register(
          "temp_tool",
          "Temporary",
          %{"type" => "object", "properties" => %{}},
          script
        )

      assert :ok = ToolRegistry.unregister("temp_tool")
      assert {:error, _} = ToolRegistry.execute("temp_tool", %{})
    end

    test "cannot unregister built-in tool" do
      assert {:error, "Cannot remove built-in tool: read_file"} =
               ToolRegistry.unregister("read_file")
    end

    test "enforces max dynamic tool limit" do
      for i <- 1..10 do
        {:ok, _} =
          ToolRegistry.register(
            "tool_#{i}",
            "Tool #{i}",
            %{"type" => "object", "properties" => %{}},
            "#!/bin/sh\necho #{i}"
          )
      end

      assert {:error, "Maximum dynamic tools (10) reached"} =
               ToolRegistry.register(
                 "tool_11",
                 "Too many",
                 %{"type" => "object", "properties" => %{}},
                 "#!/bin/sh\necho 11"
               )
    end

    test "script with non-zero exit code returns error" do
      script = """
      #!/bin/sh
      echo "something went wrong" >&2
      exit 1
      """

      {:ok, _} =
        ToolRegistry.register(
          "fail_tool",
          "Always fails",
          %{"type" => "object", "properties" => %{}},
          script
        )

      assert {:error, msg} = ToolRegistry.execute("fail_tool", %{})
      assert String.contains?(msg, "exited with code 1")
    end
  end
end
