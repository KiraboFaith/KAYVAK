// FR-11: simple care guidance for each kind of problem.
const CARE_TIPS = {
  Battery: [
    'Unplug the charger sometimes instead of keeping the battery at 100% all day.',
    'Keep the laptop away from heat, such as direct sun or a bed.',
    'Use only the charger made for your laptop.',
  ],
  'Storage drive': [
    'Shut the laptop down properly instead of holding the power button.',
    'Do not move or shake the laptop while it is working.',
    'Keep a second copy of important files on a flash disk or in the cloud.',
  ],
  'Windows licence': [
    'Buy licence keys only from trusted sellers.',
    'Avoid "activation" tools from unknown websites.',
  ],
  Security: [
    'Do not open links or attachments from people you do not know.',
    'Keep Windows and your antivirus up to date.',
    'If the laptop acts strangely, disconnect from the internet and ask for help.',
  ],
};

export function getCareTips(component) {
  return CARE_TIPS[component] || [];
}