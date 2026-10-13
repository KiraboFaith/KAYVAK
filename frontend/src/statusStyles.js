export const STATUS = {
  Good: {
    icon: '✓',
    headline: 'Your laptop is in good shape',
    message: 'All checks passed. Keep looking after it and check again soon.',
  },
  Warning: {
    icon: '!',
    headline: 'Your laptop needs a little attention',
    message:
      'Nothing has broken yet, but some parts are getting weak. Read the cards below and act soon.',
  },
  Critical: {
    icon: '✕',
    headline: 'Your laptop needs help now',
    message:
      'A serious problem was found. Follow the advice below before you use it for important work.',
  },
};

// Finds the status of one component in the report. No finding means Good.
export function statusOf(report, component) {
  const found = report.findings.find((f) => f.component === component);
  return found ? found.status : 'Good';
}