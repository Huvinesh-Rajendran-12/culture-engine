defmodule AgentHarness.NamesTest do
  use ExUnit.Case

  alias AgentHarness.Names

  test "generate returns a three-word name" do
    name = Names.generate()
    words = String.split(name, " ")
    assert length(words) == 3
  end

  test "generate returns different names" do
    names = for _ <- 1..10, do: Names.generate()
    # With 34*31*34 = ~35k combinations, 10 samples should be unique
    assert length(Enum.uniq(names)) > 1
  end
end
