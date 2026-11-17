import { useNavigate } from 'react-router-dom';
import { Compass, LayoutDashboard } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/States';

export function NotFound() {
  const navigate = useNavigate();
  return (
    <Card
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="grid-noise p-0">
      
      <EmptyState
        icon={<Compass className="h-6 w-6" />}
        title="This page isn’t part of your workspace"
        description="The route you followed doesn’t exist, or your role doesn’t grant access to it. Every access attempt is recorded in the audit log."
        action={
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/')}
          iconLeft={<LayoutDashboard className="h-3.5 w-3.5" />}>
          
            Back to Command Center
          </Button>
        }
        secondaryAction={
        <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
            Go back
          </Button>
        } />
      
    </Card>);

}