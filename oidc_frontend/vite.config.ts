import { defineConfig } from 'vite';

// Allow all hosts (e.g., ngrok, tunnels) and enable CORS for dev server
export default defineConfig({
	server: {
		host: true,
		// Vite 5: allowedHosts can be true (allow all) or string[] of hostnames
		allowedHosts: true,
		cors: true
	},
	preview: {
		allowedHosts: true,
		cors: true
	}
}); 