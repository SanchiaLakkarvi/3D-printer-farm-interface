import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata={title:"UWA 3D Print Farm",description:"Submit, track and manage 3D printing jobs at UWA.",icons:{icon:"/favicon.svg"}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
