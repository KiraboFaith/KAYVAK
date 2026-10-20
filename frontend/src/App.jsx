import ConsentGate from './components/ConsentGate';
import NotificationGate from './components/NotificationGate';
import Dashboard from './components/Dashboard';

function App() {
  return (
    <ConsentGate>
      <NotificationGate>
        <Dashboard />
      </NotificationGate>
    </ConsentGate>
  );
}

export default App;