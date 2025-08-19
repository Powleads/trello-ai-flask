// TypeScript declarations for JavaScript for Automation (JXA) globals
declare function Application(name: string): any;
declare function delay(seconds: number): void;

declare namespace Application {
  function currentApplication(): any;
}
