import { Component, StrictMode } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { DemoApp, LiveApp } from "./App";
import { BackendAccess } from "./backend";
import "./styles.css";
class BackendError extends Component<{children:ReactNode},{error:string}> {
  state={error:''};
  static getDerivedStateFromError(e:Error){return {error:e.message};}
  render(){return this.state.error?<main style={{padding:32}}><h1>Backend unavailable</h1><p role="alert">{this.state.error}</p><p>Check that the Python service is running and that your access token matches.</p><button onClick={()=>{sessionStorage.removeItem('docket.apiToken');location.reload();}}>Reconnect</button></main>:this.props.children;}
}
const demo=new URLSearchParams(location.search).has('demo');
createRoot(document.getElementById('root')!).render(<StrictMode>{demo?<DemoApp/>:<BackendError><BackendAccess><LiveApp/></BackendAccess></BackendError>}</StrictMode>);
