import ConsentGate from './components/ConsentGate';
import Dashboard from './components/Dashboard';

function App() {
  return (
    <ConsentGate>
      <Dashboard />
    </ConsentGate>
  );
}

export default App;