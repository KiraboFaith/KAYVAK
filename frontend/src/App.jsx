import { Routes, Route, useNavigate } from 'react-router-dom';
import ConsentGate from './components/ConsentGate';
import NotificationGate from './components/NotificationGate';
import Dashboard from './components/Dashboard';
import SettingsPanel from './components/SettingsPanel';
import KeyboardTest from './components/KeyboardTest';

// A simple page wrapper so Settings and Keyboard test sit on their own screen
function Page({ children }) {
  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true" />
      <div className="screen-only">{children}</div>
    </div>
  );
}

function SettingsPage() {
  const navigate = useNavigate();
  return (
    <Page>
      <SettingsPanel onClose={() => navigate('/')} />
    </Page>
  );
}

function KeyboardPage() {
  const navigate = useNavigate();
  return (
    <Page>
      <KeyboardTest onClose={() => navigate('/')} />
    </Page>
  );
}

function App() {
  return (
    <ConsentGate>
      <NotificationGate>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/keyboard" element={<KeyboardPage />} />
        </Routes>
      </NotificationGate>
    </ConsentGate>
  );
}

export default App;