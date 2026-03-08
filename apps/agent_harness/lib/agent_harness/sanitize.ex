defmodule AgentHarness.Sanitize do
  @moduledoc """
  Ensures binary output is valid UTF-8 for safe JSON encoding.

  Tool outputs (run_command, read_file, script_runner) can return raw binary
  data that contains non-UTF-8 bytes. These get stored in agent messages and
  later passed to Jason for API serialization, which crashes on invalid bytes.
  """

  @doc """
  Returns the input unchanged if it's valid UTF-8.
  Otherwise replaces invalid bytes with the Unicode replacement character (U+FFFD).
  """
  def to_valid_utf8(binary) when is_binary(binary) do
    if String.valid?(binary) do
      binary
    else
      scrub(binary, <<>>)
    end
  end

  def to_valid_utf8(other), do: other

  # Walk the binary byte-by-byte, keeping valid UTF-8 sequences and
  # replacing invalid bytes with the replacement character.
  defp scrub(<<>>, acc), do: acc

  defp scrub(binary, acc) do
    case String.next_grapheme_size(binary) do
      {size, rest} ->
        <<grapheme::binary-size(size), _::binary>> = binary
        scrub(rest, acc <> grapheme)

      nil ->
        # The first byte is invalid; skip it and insert replacement character
        <<_invalid, rest::binary>> = binary
        scrub(rest, acc <> <<0xEF, 0xBF, 0xBD>>)
    end
  end
end
