defmodule AgentHarness.Names do
  @moduledoc """
  Culture-style ship name generator.

  Generates names in the pattern "Adverb Verb Noun" like
  "Quietly Considering Ambiguity" or "Gravely Mistaken Pedagogy".
  """

  @adverbs ~w(
    Quietly Softly Gently Gravely Sweetly Merely Barely Deeply Keenly Wholly
    Calmly Subtly Fondly Oddly Wryly Deftly Purely Justly Vastly Mildly
    Sleepily Earnestly Politely Obliquely Serenely Fiercely Tenderly
    Reluctantly Cheerfully Cautiously Steadily Absently Faintly Briskly
  )

  @verbs ~w(
    Considering Contemplating Questioning Mistaking Regarding Observing
    Doubting Pursuing Embracing Forgetting Abandoning Discovering Pondering
    Surveying Weighing Drifting Anticipating Composing Illuminating
    Investigating Navigating Wondering Evaluating Appreciating Recalling
    Imagining Celebrating Challenging Deciphering Witnessing Measuring
  )

  @nouns ~w(
    Ambiguity Serenity Infinity Diplomacy Pedagogy Entropy Irony Paradox
    Tranquility Gravity Brevity Clarity Mercy Solitude Eloquence Substance
    Nuance Latitude Coincidence Consequence Equilibrium Persistence Resonance
    Symmetry Turbulence Perspective Elegance Momentum Convergence Temperance
    Diligence Providence Circumstance Magnificence
  )

  @doc "Generates a random Culture-style ship name."
  def generate do
    adverb = Enum.random(@adverbs)
    verb = Enum.random(@verbs)
    noun = Enum.random(@nouns)
    "#{adverb} #{verb} #{noun}"
  end
end
