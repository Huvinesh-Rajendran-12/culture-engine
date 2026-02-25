defmodule AgentHarness.ToolRegistryTest do
  use ExUnit.Case

  alias AgentHarness.ToolRegistry

  test "all_definitions returns tool definitions" do
    defs = ToolRegistry.all_definitions()
    assert length(defs) == 3

    names = Enum.map(defs, & &1["name"])
    assert "read_file" in names
    assert "list_files" in names
    assert "edit_file" in names

    for def <- defs do
      assert Map.has_key?(def, "name")
      assert Map.has_key?(def, "description")
      assert Map.has_key?(def, "input_schema")
    end
  end

  test "execute read_file reads an existing file" do
    path = Path.join(System.tmp_dir!(), "harness_test_read.txt")
    File.write!(path, "hello agent")

    assert {:ok, "hello agent"} = ToolRegistry.execute("read_file", %{"path" => path})

    File.rm!(path)
  end

  test "execute read_file returns error for missing file" do
    assert {:error, _} = ToolRegistry.execute("read_file", %{"path" => "/tmp/nonexistent_xyz"})
  end

  test "execute list_files lists directory contents" do
    dir = Path.join(System.tmp_dir!(), "harness_test_list")
    File.mkdir_p!(dir)
    File.write!(Path.join(dir, "a.txt"), "a")
    File.mkdir_p!(Path.join(dir, "subdir"))

    {:ok, json} = ToolRegistry.execute("list_files", %{"path" => dir})
    items = Jason.decode!(json)

    assert "a.txt" in items
    assert "subdir/" in items

    File.rm_rf!(dir)
  end

  test "execute edit_file creates a new file" do
    path = Path.join(System.tmp_dir!(), "harness_test_create.txt")
    File.rm(path)

    assert {:ok, _} =
             ToolRegistry.execute("edit_file", %{
               "path" => path,
               "old_string" => "",
               "new_string" => "new content"
             })

    assert File.read!(path) == "new content"
    File.rm!(path)
  end

  test "execute edit_file replaces content" do
    path = Path.join(System.tmp_dir!(), "harness_test_edit.txt")
    File.write!(path, "hello world")

    assert {:ok, _} =
             ToolRegistry.execute("edit_file", %{
               "path" => path,
               "old_string" => "world",
               "new_string" => "agent"
             })

    assert File.read!(path) == "hello agent"
    File.rm!(path)
  end

  test "execute unknown tool returns error" do
    assert {:error, "Unknown tool: nope"} = ToolRegistry.execute("nope", %{})
  end
end
