# PSEUDO-AGENT SPEC (human + CLI hybrid)
# command: expand-ability <seed_ability> --n=20 --gradient=mechanism->constraint
# behavior:
# - keep same causal domain
# - vary trigger, scope, cost, precision
# - no lore, no characters


abilities {

  # === Seed: FLIGHT ===
  "Flight" {
    description: "Sustained self-directed movement through air independent of lift surfaces."

    gradient {
      "Float" { description: "Passive buoyancy allowing slow vertical drift without directional control." }
      "Levitation" { description: "Stationary suspension in midair requiring concentration to maintain." }
      "Glide" { description: "Unpowered aerial descent with limited horizontal control." }
      "Aerial Walking" { description: "Treating air as a solid surface for locomotion." }
      "Vector Flight" { description: "Directional propulsion allowing rapid acceleration and braking." }
      "Hover Lock" { description: "Absolute positional stability in three-dimensional space." }
      "Atmospheric Skimming" { description: "High-speed flight constrained to surfaces or terrain contours." }
      "Burst Lift" { description: "Short-duration vertical launch followed by gravity reassertion." }
      "Wing Manifestation" { description: "Temporary biological or energetic appendages enabling lift." }
      "Gravitic Negation" { description: "Local cancellation of gravitational pull on the user." }
      "Air Density Manipulation" { description: "Increasing atmospheric density to support body weight." }
      "Self-Orbit" { description: "Maintaining stable orbit around a nearby massive object." }
      "Inertial Flight" { description: "Movement through air without inertia transfer to surroundings." }
      "Supersonic Transit" { description: "High-velocity flight exceeding sound barriers without shockwaves." }
      "Hover Sleep" { description: "Unconscious or resting flight state without loss of altitude." }
      "Altitude Immunity" { description: "No physiological penalty from extreme elevation during flight." }
      "Directional Arrest" { description: "Instant halt of all aerial momentum." }
      "Shared Lift" { description: "Extending flight capability to touched entities." }
      "Payload Flight" { description: "Maintaining flight regardless of carried mass." }
      "Silent Flight" { description: "Aerial movement producing no acoustic disturbance." }
    }
  }

  # === Seed: TELEPATHY ===
  "Telepathy" {
    description: "Direct transmission and reception of thoughts between conscious minds."

    gradient {
      "Surface Thought Reading" { description: "Perceiving active, unguarded thoughts only." }
      "Deep Memory Access" { description: "Retrieval of long-term memories without emotional context." }
      "Emotion Sensing" { description: "Detection of emotional states without semantic content." }
      "Mind Whisper" { description: "Injecting brief, subtle thoughts mistaken for self-originated." }
      "Cognitive Broadcast" { description: "Projecting thoughts to multiple minds simultaneously." }
      "Mental Encryption" { description: "Shielding thoughts behind psychic ciphers." }
      "Thought Suppression" { description: "Temporarily silencing conscious thought in a target." }
      "Psionic Link" { description: "Establishing persistent two-way mental communication." }
      "Memory Imprint" { description: "Planting fabricated memories with low long-term stability." }
      "Belief Reinforcement" { description: "Strengthening existing convictions without introducing new ones." }
      "Telepathic Overload" { description: "Flooding the mind with simultaneous thought streams." }
      "Language-Agnostic Comprehension" { description: "Understanding intent independent of linguistic form." }
      "Dream Telepathy" { description: "Mental interaction with sleeping or unconscious targets." }
      "Cognitive Eavesdropping" { description: "Passive interception of nearby mental communications." }
      "Identity Blur" { description: "Causing targets to misattribute thoughts to the wrong source." }
      "Psionic Silence" { description: "Nullifying all telepathic activity in a defined area." }
      "Mental Fingerprint" { description: "Recognizing individuals by unique thought patterns." }
      "Thought Looping" { description: "Forcing repetition of specific mental constructs." }
      "Will Dampening" { description: "Reducing resistance to external mental influence." }
      "Monologue Compulsion" { description: "Inducing an uncontrollable urge to verbally explain intentions and plans." }
    }
  }
}

