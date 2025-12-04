import React, { useState } from 'react';
import {
  Box,
  Dialog,
  DialogContent,
} from '@mui/material';
import MonitorCreationWizard from './pulse/MonitorCreationWizard';
import MonitorDashboard from './pulse/MonitorDashboard';

const EnterprisePulse = () => {
  // Use fixed 'persona' ID for persona-based insights
  const userId = 'persona';
  const [showWizard, setShowWizard] = useState(false);

  return (
    <Box sx={{
      p: 3,
      height: '100%',
      overflowY: 'auto',
      overflowX: 'hidden',
      bgcolor: '#f5f5f5'
    }}>
      {/* Monitor Creation Wizard Dialog */}
      <Dialog
        open={showWizard}
        onClose={() => setShowWizard(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogContent>
          <MonitorCreationWizard
            userId={userId}
            onClose={() => setShowWizard(false)}
            onSave={() => {
              setShowWizard(false);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Main Dashboard */}
      <MonitorDashboard
        userId={userId}
        onCreateMonitor={() => setShowWizard(true)}
      />
    </Box>
  );
};

export default EnterprisePulse;
