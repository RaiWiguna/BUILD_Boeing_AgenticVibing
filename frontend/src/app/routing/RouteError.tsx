import { isRouteErrorResponse, Link, useRouteError } from 'react-router';
import { Compass } from 'lucide-react';
import { Card } from '@/components/domain/primitives';
import { EmptyState, ErrorState } from '@/components/domain/states';
import { Button } from '@/components/ui/button';

export function RouteError() {
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFound />;
  return (
    <div className="p-8">
      <Card className="mx-auto max-w-xl">
        <ErrorState error={error} onRetry={() => window.location.reload()} />
      </Card>
    </div>
  );
}

export function NotFound() {
  return (
    <Card className="mx-auto mt-10 max-w-xl">
      <EmptyState icon={Compass} title="Page not found" action={<Button asChild variant="primary"><Link to="/sessions">Go to sessions</Link></Button>}>
        The address does not match a FlowLens page or a session shared with you.
      </EmptyState>
    </Card>
  );
}
