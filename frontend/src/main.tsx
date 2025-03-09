import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { store } from './store'
import App from './App'
import './styles/globals.css'
import AOS from 'aos'
import 'aos/dist/aos.css'

// 初始化AOS
AOS.init({
  duration: 800,
  easing: 'ease-out',
  once: false,
  mirror: false,
  offset: 120,
})

// 渲染应用
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>,
)
