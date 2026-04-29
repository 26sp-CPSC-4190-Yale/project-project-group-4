import { useState, useRef } from 'react'
import { SWIPE_THRESHOLD } from '../lib/constants'

/**
 * Custom hook for card swipe + tap-to-flip gesture handling.
 * Returns drag state, flip state, computed transforms, and event handlers.
 */
export default function useSwipe(onSwipe) {
  const [dragX, setDragX] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [exiting, setExiting] = useState(null)
  const [flipped, setFlipped] = useState(false)

  const startXRef = useRef(null)
  const hasDraggedRef = useRef(false)

  function handleSwipe(direction) {
    if (exiting) return
    setExiting(direction)
    setTimeout(() => {
      onSwipe(direction)
      setExiting(null)
      setDragX(0)
      setFlipped(false)
    }, 350)
  }

  function onPointerStart(clientX) {
    if (exiting) return
    startXRef.current = clientX
    hasDraggedRef.current = false
    setDragging(true)
  }

  function onPointerMove(clientX) {
    if (startXRef.current === null || exiting) return
    const dx = clientX - startXRef.current
    if (Math.abs(dx) > 5) hasDraggedRef.current = true
    setDragX(dx)
  }

  function onPointerEnd() {
    if (startXRef.current === null || exiting) return
    if (!hasDraggedRef.current) {
      setFlipped(f => !f)
    } else if (Math.abs(dragX) >= SWIPE_THRESHOLD) {
      handleSwipe(dragX > 0 ? 'right' : 'left')
    } else {
      setDragX(0)
    }
    startXRef.current = null
    setDragging(false)
  }

  // Computed values for rendering
  const rotation = dragX / 20
  const likeOpacity = Math.max(0, Math.min(dragX / SWIPE_THRESHOLD, 1))
  const passOpacity = Math.max(0, Math.min(-dragX / SWIPE_THRESHOLD, 1))

  let cardTransform, cardTransition
  if (exiting) {
    const dir = exiting === 'right' ? 1 : -1
    cardTransform = `translateX(${dir * 800}px) rotate(${dir * 25}deg)`
    cardTransition = 'transform 0.35s ease-in'
  } else {
    cardTransform = `translateX(${dragX}px) rotate(${rotation}deg)`
    cardTransition = dragging ? 'none' : 'transform 0.3s ease'
  }

  // Props to spread onto the card element
  const cardProps = {
    style: {
      transform: cardTransform,
      transition: cardTransition,
      pointerEvents: exiting ? 'none' : 'auto',
    },
    onTouchStart: e => onPointerStart(e.touches[0].clientX),
    onTouchMove: e => onPointerMove(e.touches[0].clientX),
    onTouchEnd: onPointerEnd,
    onMouseDown: e => onPointerStart(e.clientX),
    onMouseMove: e => { if (dragging) onPointerMove(e.clientX) },
    onMouseUp: onPointerEnd,
    onMouseLeave: () => { if (dragging) onPointerEnd() },
  }

  return {
    flipped,
    likeOpacity,
    passOpacity,
    exiting,
    cardProps,
    handleSwipe,
  }
}
