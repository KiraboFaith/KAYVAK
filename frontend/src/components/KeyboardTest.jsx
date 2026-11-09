import { useEffect, useState } from 'react';
import './KeyboardTest.css';

// Each key: [KeyboardEvent.code, label shown, width]. "code" names the physical key,
// whatever the keyboard layout, so it is the right thing to test.
const k = (code, label = code, width = 1) => ({ code, label, width });
const letters = (text) => [...text].map((c) => k(`Key${c}`, c));
const digits = [...'1234567890'].map((c) => k(`Digit${c}`, c));

const ROWS = [
  [k('Escape', 'Esc'), ...Array.from({ length: 12 }, (_, i) => k(`F${i + 1}`)), k('Delete', 'Del')],
  [k('Backquote', '`'), ...digits, k('Minus', '-'), k('Equal', '='), k('Backspace', 'Backspace', 2)],
  [k('Tab', 'Tab', 1.5), ...letters('QWERTYUIOP'), k('BracketLeft', '['), k('BracketRight', ']'), k('Backslash', '\\', 1.5)],
  [k('CapsLock', 'Caps', 1.75), ...letters('ASDFGHJKL'), k('Semicolon', ';'), k('Quote', "'"), k('Enter', 'Enter', 2.25)],
  [k('ShiftLeft', 'Shift', 2.25), ...letters('ZXCVBNM'), k('Comma', ','), k('Period', '.'), k('Slash', '/'), k('ShiftRight', 'Shift', 2.75)],
  [
    k('ControlLeft', 'Ctrl', 1.25), k('MetaLeft', 'Win', 1.25), k('AltLeft', 'Alt', 1.25),
    k('Space', 'Space', 6.25), k('AltRight', 'Alt', 1.25), k('ControlRight', 'Ctrl', 1.25),
    k('ArrowLeft', '←'), k('ArrowUp', '↑'), k('ArrowDown', '↓'), k('ArrowRight', '→'),
  ],
];
const ALL_CODES = ROWS.flat().map((key) => key.code);

// Lights up each key as it is pressed, so a dead key shows as one that never lights up.
function KeyboardTest({ onClose }) {
  const [pressed, setPressed] = useState(() => new Set()); // keys that worked at least once
  const [down, setDown] = useState(() => new Set()); // keys held right now
  const [skipped, setSkipped] = useState(() => new Set()); // keys this laptop does not have
  const [other, setOther] = useState([]); // keys that are not on the drawing (numpad, etc.)

  useEffect(() => {
    const press = (event) => {
      event.preventDefault(); // stop F5, Tab, F1 and similar from doing their normal job
      const code = event.code;
      if (!ALL_CODES.includes(code)) {
        setOther((list) => (list.includes(code) ? list : [...list, code]));
        return;
      }
      setPressed((set) => new Set(set).add(code));
      setDown((set) => new Set(set).add(code));
    };
    const release = (event) => {
      if (ALL_CODES.includes(event.code)) {
        // PrintScreen only sends a key-up on Windows, so count that as a press too.
        setPressed((set) => new Set(set).add(event.code));
        setDown((set) => {
          const next = new Set(set);
          next.delete(event.code);
          return next;
        });
      }
    };
    window.addEventListener('keydown', press);
    window.addEventListener('keyup', release);
    return () => {
      window.removeEventListener('keydown', press);
      window.removeEventListener('keyup', release);
    };
  }, []);

  const toggleSkipped = (code) =>
    setSkipped((set) => {
      const next = new Set(set);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });

  const reset = () => {
    setPressed(new Set());
    setDown(new Set());
    setSkipped(new Set());
    setOther([]);
  };

  const needed = ALL_CODES.filter((code) => !skipped.has(code));
  const done = needed.filter((code) => pressed.has(code));
  const missing = needed.filter((code) => !pressed.has(code));
  const labelOf = (code) => ROWS.flat().find((key) => key.code === code).label;

  return (
    <section className="card kbd" aria-label="Keyboard test">
      <div className="section-head">
        <h2>Keyboard test</h2>
        <div>
          <button className="btn btn-quiet" onClick={reset}>Start again</button>{' '}
          <button className="btn btn-quiet" onClick={onClose}>Close</button>
        </div>
      </div>
      <p className="snap-note">
        Press every key. Each one lights up green when it works. One dead key does not mean the
        whole keyboard needs replacing. Click a key to mark it as one this laptop does not have.
        Use the Close button to leave (Esc is a key to test).
      </p>

      <div className="kbd-board">
        {ROWS.map((row, r) => (
          <div className="kbd-row" key={r}>
            {row.map((key) => (
              <button
                key={key.code}
                type="button"
                className="kbd-key"
                style={{ flex: key.width }}
                data-state={
                  skipped.has(key.code) ? 'skipped' : down.has(key.code) ? 'down' : pressed.has(key.code) ? 'ok' : 'waiting'
                }
                onClick={() => toggleSkipped(key.code)}
                onKeyDown={(e) => e.preventDefault()}
              >
                {key.label}
              </button>
            ))}
          </div>
        ))}
      </div>

      <p className="kbd-progress">
        <strong>{done.length}</strong> of <strong>{needed.length}</strong> keys tested.
        {missing.length === 0 && needed.length > 0 && ' Every key works.'}
      </p>
      {missing.length > 0 && missing.length <= 15 && (
        <p className="snap-note">Not pressed yet: {missing.map(labelOf).join(', ')}</p>
      )}
      {other.length > 0 && <p className="snap-note">Other keys that worked: {other.join(', ')}</p>}
      <p className="snap-note">
        The Fn key, and some media keys, never reach the browser, so they cannot be tested here.
        Windows shortcuts such as Alt+Tab also cannot be caught.
      </p>
    </section>
  );
}

export default KeyboardTest;