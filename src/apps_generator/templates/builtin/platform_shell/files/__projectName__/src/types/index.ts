export interface Tenant {
  id: string;
  name: string;
  slug?: string;
}

export interface RemotePage {
  path: string;
  label: string;
  icon?: string;
}

export interface RemoteApp {
  name: string;
  url: string;
  menuLabel: string;
  menuIcon?: string;
  pages?: RemotePage[];
}

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
}
